"""Keyword retrieval with PostgreSQL full-text search (P4-T3).

FR-RET-002, FR-RET-003, FR-RET-004; configuration and reasons in
docs/design/retrieval.md. The question is always a bound parameter and is
treated as data: its words are looked up, and nothing in it acts as an operator.

Scores come from ts_rank and are only comparable within one query. They are
not a confidence or a probability.

Logs carry counts only, never the question or passage text (NFR-PRI-002).
"""

import logging
import uuid
from collections.abc import Collection
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Text, cast, func, select
from sqlalchemy.dialects.postgresql import TSQUERY
from sqlalchemy.orm import Session, sessionmaker

from app.models import Document, Passage
from app.models.passage import SEARCH_CONFIG

logger = logging.getLogger(__name__)


class QueryTooLongError(Exception):
    """The question is longer than allowed. `message` never repeats it."""

    code = "query_too_long"

    def __init__(self, max_chars: int) -> None:
        super().__init__(self.code)
        self.max_chars = max_chars
        self.message = f"The question is too long. The limit is {max_chars} characters."


@dataclass(frozen=True)
class RetrievedPassage:
    """A stored passage and where it is. Null section or page means unknown."""

    passage_id: uuid.UUID
    document_id: uuid.UUID
    paper_id: uuid.UUID
    section: str | None
    page_start: int | None
    page_end: int | None
    text: str
    score: float


def clean_question(raw: str, *, max_chars: int) -> str:
    """Remove what the database driver cannot accept, then enforce the limit.

    NUL characters and unpaired surrogates carry no meaning but raise errors
    before a query can run. Over-long questions exhaust PostgreSQL's stack.
    """
    question = raw.replace("\x00", " ").encode("utf-8", "ignore").decode("utf-8")
    if len(question) > max_chars:
        raise QueryTooLongError(max_chars)
    return question


def _any_word_query(question: str) -> ColumnElement[str]:
    """A tsquery matching passages with any of the question's words.

    plainto_tsquery ignores operators in its input and joins words with AND,
    which is too strict for a question, so the ANDs become ORs.
    """
    all_words = cast(func.plainto_tsquery(SEARCH_CONFIG, question), Text)
    return cast(func.replace(all_words, " & ", " | "), TSQUERY)


def search_passages(
    sessions: sessionmaker[Session],
    question: str,
    *,
    k: int,
    max_query_chars: int,
    document_ids: Collection[uuid.UUID] | None = None,
    paper_ids: Collection[uuid.UUID] | None = None,
) -> list[RetrievedPassage]:
    """The `k` best passages from `parsed` documents in scope, best first.

    `None` means no restriction by that field; an empty collection means
    nothing is in scope. When both are given, a passage must satisfy both. No
    match, and an unknown id, give an empty list. Raises QueryTooLongError.
    """
    if k < 1:
        raise ValueError("k must be positive")
    query = _any_word_query(clean_question(question, max_chars=max_query_chars))
    rank = func.ts_rank(Passage.search_vector, query)
    statement = (
        select(
            Passage.id,
            Passage.document_id,
            Document.paper_id,
            Passage.section_path,
            Passage.page_start,
            Passage.page_end,
            Passage.text,
            rank.label("score"),
        )
        .join(Document, Passage.document_id == Document.id)
        .where(Document.status == "parsed", Passage.search_vector.op("@@")(query))
        .order_by(rank.desc(), Passage.id)
        .limit(k)
    )
    if document_ids is not None:
        statement = statement.where(Passage.document_id.in_(document_ids))
    if paper_ids is not None:
        statement = statement.where(Document.paper_id.in_(paper_ids))

    with sessions() as session:
        rows = session.execute(statement).all()
    logger.info("retrieval k=%d results=%d", k, len(rows))
    return [
        RetrievedPassage(
            passage_id=row.id,
            document_id=row.document_id,
            paper_id=row.paper_id,
            section=row.section_path,
            page_start=row.page_start,
            page_end=row.page_end,
            text=row.text,
            score=float(row.score),
        )
        for row in rows
    ]

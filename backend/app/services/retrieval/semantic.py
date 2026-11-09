"""Semantic retrieval by cosine distance in pgvector (R3; FR-RET-005).

Same scope and `k` meaning as keyword retrieval, and only `parsed` documents.
Search is exact, for the reasons in docs/design/embeddings.md. The score is
cosine similarity: comparable only within one query, and never a confidence.

Semantic search always has a nearest passage, so a result does not mean the
passage is relevant. Passages without an embedding from this model are counted
and reported, not skipped silently.

Logs carry counts only, never the question or passage text (NFR-PRI-002).
"""

import logging
import uuid
from collections.abc import Collection
from dataclasses import dataclass

from sqlalchemy import Float, Select, and_, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Document, Passage, PassageEmbedding
from app.services.embeddings import Embedder
from app.services.retrieval.embedding_job import refuse_a_different_size
from app.services.retrieval.keyword import RetrievedPassage, clean_question

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SemanticResult:
    passages: list[RetrievedPassage]
    missing_embeddings: int  # in scope, for this model


def _in_scope[*Ts](
    statement: Select[*Ts],
    document_ids: Collection[uuid.UUID] | None,
    paper_ids: Collection[uuid.UUID] | None,
) -> Select[*Ts]:
    if document_ids is not None:
        statement = statement.where(Passage.document_id.in_(document_ids))
    if paper_ids is not None:
        statement = statement.where(Document.paper_id.in_(paper_ids))
    return statement


def _coverage(
    sessions: sessionmaker[Session],
    model: str,
    document_ids: Collection[uuid.UUID] | None,
    paper_ids: Collection[uuid.UUID] | None,
) -> tuple[int, int]:
    """(passages in scope, those with an embedding from `model`)."""
    statement = (
        select(func.count(Passage.id), func.count(PassageEmbedding.id))
        .select_from(Passage)
        .join(Document, Passage.document_id == Document.id)
        .outerjoin(
            PassageEmbedding,
            and_(
                PassageEmbedding.passage_id == Passage.id,
                PassageEmbedding.model == model,
            ),
        )
        .where(Document.status == "parsed")
    )
    with sessions() as session:
        total, embedded = session.execute(
            _in_scope(statement, document_ids, paper_ids)
        ).one()
    return int(total), int(embedded)


def search_semantic(
    sessions: sessionmaker[Session],
    embedder: Embedder,
    question: str,
    *,
    k: int,
    max_query_chars: int,
    document_ids: Collection[uuid.UUID] | None = None,
    paper_ids: Collection[uuid.UUID] | None = None,
) -> SemanticResult:
    """The `k` nearest passages in scope, best first.

    Nothing is sent to the provider when the question is blank or no passage
    in scope has an embedding. Raises QueryTooLongError, or a `ModelError` if
    the stored size differs or the provider fails.
    """
    if k < 1:
        raise ValueError("k must be positive")
    cleaned = clean_question(question, max_chars=max_query_chars)
    refuse_a_different_size(sessions, embedder)
    model = embedder.model_name
    total, embedded = _coverage(sessions, model, document_ids, paper_ids)
    missing = total - embedded
    if embedded == 0 or not cleaned.strip():
        return SemanticResult([], missing)

    distance = PassageEmbedding.embedding.op("<=>", return_type=Float())(
        embedder.embed_query(cleaned)
    )
    statement = (
        select(
            Passage.id,
            Passage.document_id,
            Document.paper_id,
            Passage.section_path,
            Passage.page_start,
            Passage.page_end,
            Passage.text,
            (1 - distance).label("score"),
        )
        .join(PassageEmbedding, PassageEmbedding.passage_id == Passage.id)
        .join(Document, Passage.document_id == Document.id)
        .where(Document.status == "parsed", PassageEmbedding.model == model)
        .order_by(distance, Passage.id)
        .limit(k)
    )
    with sessions() as session:
        rows = session.execute(_in_scope(statement, document_ids, paper_ids)).all()
    logger.info("semantic k=%d results=%d missing=%d", k, len(rows), missing)
    return SemanticResult(
        [
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
        ],
        missing,
    )

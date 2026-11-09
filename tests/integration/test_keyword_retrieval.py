"""Keyword retrieval against PostgreSQL (P4-T3; FR-RET-002, FR-RET-003, FR-RET-004).

Passages are synthetic. Hostile input and scope isolation are covered further
in P4-T4.
"""

import hashlib
import itertools
import uuid
from collections.abc import Collection
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.models import Document, Paper, Passage
from app.services.retrieval.keyword import (
    QueryTooLongError,
    RetrievedPassage,
    search_passages,
)

_n = itertools.count()
MAX_CHARS = 2000


def add_paper(sessions: sessionmaker[Session]) -> uuid.UUID:
    with sessions.begin() as session:
        paper = Paper(metadata_source="grobid")
        session.add(paper)
        session.flush()
        return paper.id


def add_document(
    sessions: sessionmaker[Session],
    *passages: str | dict[str, Any],
    paper_id: uuid.UUID | None = None,
    status: str = "parsed",
) -> uuid.UUID:
    """A document holding `passages`, each a text or a dict of column values."""
    n = next(_n)
    values: dict[str, Any] = {}
    if status == "parsed":
        values = {
            "paper_id": paper_id or add_paper(sessions),
            "parser_name": "grobid",
            "parser_version": "0.9.1",
            "tei_storage_key": f"tei/k{n}",
        }
    if status == "failed":
        values = {"failure_reason": "parser_busy"}
    if status == "processing":
        values = {"processing_started_at": datetime.now(UTC)}
    with sessions.begin() as session:
        document = Document(
            sha256=hashlib.sha256(f"retrieval-{n}".encode()).hexdigest(),
            size_bytes=10,
            storage_key=f"pdf/k{n}",
            status=status,
            **values,
        )
        session.add(document)
        session.flush()
        for ordinal, passage in enumerate(passages):
            row = {"text": passage} if isinstance(passage, str) else passage
            session.add(
                Passage(
                    document_id=document.id,
                    ordinal=ordinal,
                    **{"region": "body", **row},
                )
            )
        return document.id


def search(
    sessions: sessionmaker[Session],
    question: str,
    *,
    k: int = 5,
    document_ids: Collection[uuid.UUID] | None = None,
    paper_ids: Collection[uuid.UUID] | None = None,
) -> list[RetrievedPassage]:
    return search_passages(
        sessions,
        question,
        k=k,
        max_query_chars=MAX_CHARS,
        document_ids=document_ids,
        paper_ids=paper_ids,
    )


def texts(results: list[RetrievedPassage]) -> list[str]:
    return [result.text for result in results]


# --- What comes back --------------------------------------------------------


def test_result_carries_the_stored_location_and_text(
    sessions: sessionmaker[Session],
) -> None:
    paper_id = add_paper(sessions)
    document_id = add_document(
        sessions,
        {
            "text": "Glaciers retreated   quickly.",
            "section_number": "2",
            "section_title": "Results",
            "page_start": 3,
            "page_end": 4,
        },
        paper_id=paper_id,
    )

    [result] = search(sessions, "glacier")

    assert result.document_id == document_id
    assert result.paper_id == paper_id
    assert result.section == "2 Results"
    assert (result.page_start, result.page_end) == (3, 4)
    assert result.text == "Glaciers retreated   quickly."
    assert isinstance(result.passage_id, uuid.UUID)
    assert result.score > 0


def test_unknown_section_and_page_stay_null(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "Glaciers retreated.")

    [result] = search(sessions, "glacier")

    assert (result.section, result.page_start, result.page_end) == (None, None, None)


def test_no_match_returns_an_empty_list(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "Glaciers retreated.")

    assert search(sessions, "volcano") == []


# --- Matching and ranking ---------------------------------------------------


def test_a_passage_needs_only_some_of_the_question_words(
    sessions: sessionmaker[Session],
) -> None:
    """OR, not AND: docs/design/retrieval.md §3."""
    add_document(sessions, "Glaciers retreated quickly.")

    assert len(search(sessions, "why did mountain glaciers vanish so fast")) == 1


def test_word_forms_match(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "The experiments were replicated.")

    assert len(search(sessions, "replication of an experiment")) == 1


def test_more_matching_words_rank_higher(sessions: sessionmaker[Session]) -> None:
    add_document(
        sessions,
        "Glaciers appear here once with unrelated words alongside.",
        "Glaciers retreat and glacier retreat continued as glaciers retreated.",
    )

    results = search(sessions, "glacier retreat")

    assert texts(results)[0].startswith("Glaciers retreat and")
    assert results[0].score > results[1].score


def test_equal_scores_have_a_fixed_order(sessions: sessionmaker[Session]) -> None:
    """Ids are stored in reverse, so insertion order cannot pass for the tie-break."""
    ids = sorted(uuid.uuid4() for _ in range(8))
    add_document(
        sessions, *[{"id": i, "text": "Glaciers retreated."} for i in reversed(ids)]
    )

    assert [r.passage_id for r in search(sessions, "glacier", k=8)] == ids
    assert [r.passage_id for r in search(sessions, "glacier", k=3)] == ids[:3]


# --- Limit -------------------------------------------------------------------


def test_k_limits_the_results(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, *["Glaciers retreated."] * 8)

    assert len(search(sessions, "glacier", k=3)) == 3


@pytest.mark.parametrize("k", [0, -1])
def test_k_must_be_positive(sessions: sessionmaker[Session], k: int) -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        search(sessions, "glacier", k=k)


# --- Scope -------------------------------------------------------------------


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_only_parsed_documents_are_searched(
    sessions: sessionmaker[Session], status: str
) -> None:
    add_document(sessions, "Glaciers retreated.", status=status)

    assert search(sessions, "glacier") == []


def test_scope_by_document(sessions: sessionmaker[Session]) -> None:
    wanted = add_document(sessions, "Glaciers in the wanted document.")
    add_document(sessions, "Glaciers in the other document.")

    results = search(sessions, "glacier", document_ids=[wanted])

    assert [result.document_id for result in results] == [wanted]


def test_scope_by_paper_covers_all_its_documents(
    sessions: sessionmaker[Session],
) -> None:
    paper_id = add_paper(sessions)
    wanted = {
        add_document(sessions, "Glaciers one.", paper_id=paper_id),
        add_document(sessions, "Glaciers two.", paper_id=paper_id),
    }
    add_document(sessions, "Glaciers elsewhere.")

    results = search(sessions, "glacier", paper_ids=[paper_id])

    assert {result.document_id for result in results} == wanted


def test_document_and_paper_scope_must_both_hold(
    sessions: sessionmaker[Session],
) -> None:
    paper_id = add_paper(sessions)
    inside = add_document(sessions, "Glaciers inside.", paper_id=paper_id)
    outside = add_document(sessions, "Glaciers outside.")

    results = search(
        sessions, "glacier", document_ids=[inside, outside], paper_ids=[paper_id]
    )

    assert [result.document_id for result in results] == [inside]


def test_empty_scope_finds_nothing_rather_than_everything(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated.")

    assert search(sessions, "glacier", document_ids=[]) == []
    assert search(sessions, "glacier", paper_ids=[]) == []


def test_unknown_scope_id_finds_nothing(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "Glaciers retreated.")

    assert search(sessions, "glacier", document_ids=[uuid.uuid4()]) == []
    assert search(sessions, "glacier", paper_ids=[uuid.uuid4()]) == []


# --- Input the database would otherwise fail on (docs/design/retrieval.md §3) ---


def test_question_over_the_limit_is_rejected(sessions: sessionmaker[Session]) -> None:
    with pytest.raises(QueryTooLongError) as caught:
        search(sessions, "x" * (MAX_CHARS + 1))

    assert caught.value.code == "query_too_long"


def test_question_at_the_limit_with_the_most_terms_possible_works(
    sessions: sessionmaker[Session],
) -> None:
    """The limit must sit below the size at which PostgreSQL itself fails."""
    add_document(sessions, "Glaciers retreated.")
    question = (
        " ".join(f"{i:x}" for i in range(MAX_CHARS))[: MAX_CHARS - 8] + " glacier"
    )
    assert len(question) <= MAX_CHARS

    assert len(search(sessions, question)) == 1


@pytest.mark.parametrize(
    "question", ["glacier\x00retreat", "glacier \ud800 retreat", "\x00glacier"]
)
def test_characters_the_driver_rejects_are_removed(
    sessions: sessionmaker[Session], question: str
) -> None:
    add_document(sessions, "Glaciers retreated.")

    assert len(search(sessions, question)) == 1

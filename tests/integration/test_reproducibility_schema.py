"""Assessment tables and the passages a labeller sees (R5; FR-REP-002, AD-013)."""

import uuid
from typing import Any

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.evaluation.reproducibility_labels import load_paper
from tests.integration.test_keyword_retrieval import add_document

from app.models import (
    Passage,
    ReproducibilityAssessment,
    ReproducibilityItem,
    ReproducibilityItemPassage,
)


def add_assessment(
    sessions: sessionmaker[Session], document: uuid.UUID, **values: Any
) -> uuid.UUID:
    with sessions.begin() as session:
        assessment = ReproducibilityAssessment(
            **{
                "document_id": document,
                "checklist_version": "checklist-v1",
                "document_status": "parsed",
                "model": "m",
                "prompt_version": "p",
                **values,
            }
        )
        session.add(assessment)
        session.flush()
        return assessment.id


def add_item(
    sessions: sessionmaker[Session], assessment: uuid.UUID, **values: Any
) -> uuid.UUID:
    with sessions.begin() as session:
        item = ReproducibilityItem(
            **{
                "assessment_id": assessment,
                "item_key": "code_availability",
                "status": "reported",
                **values,
            }
        )
        session.add(item)
        session.flush()
        return item.id


@pytest.fixture
def document(sessions: sessionmaker[Session]) -> uuid.UUID:
    return add_document(sessions, "A passage.")


def passage_of(sessions: sessionmaker[Session], document: uuid.UUID) -> uuid.UUID:
    with sessions() as session:
        return session.scalars(
            select(Passage.id).where(Passage.document_id == document)
        ).one()


def test_a_complete_assessment_is_stored_with_its_provenance(
    sessions: sessionmaker[Session], document: uuid.UUID
) -> None:
    assessment = add_assessment(sessions, document)
    item = add_item(sessions, assessment, explanation="Stated in the methods.")
    passage = passage_of(sessions, document)
    with sessions.begin() as session:
        session.add(
            ReproducibilityItemPassage(item_id=item, passage_id=passage, quote="A pass")
        )

    with sessions() as session:
        stored = session.get_one(ReproducibilityAssessment, assessment)
        link = session.scalars(select(ReproducibilityItemPassage)).one()
    assert stored.checklist_version == "checklist-v1"
    assert (stored.model, stored.prompt_version) == ("m", "p")
    assert stored.created_at is not None
    assert (link.item_id, link.passage_id, link.quote) == (item, passage, "A pass")


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({"checklist_version": ""}, id="empty version"),
        pytest.param({"document_status": "other"}, id="unknown document status"),
        pytest.param({"model": ""}, id="empty model"),
        pytest.param({"prompt_version": ""}, id="empty prompt"),
        pytest.param({"prompt_version": None}, id="model without prompt"),
        pytest.param({"model": None}, id="prompt without model"),
        pytest.param({"retrieval_method": ""}, id="empty retrieval method"),
    ],
)
def test_an_inconsistent_assessment_is_refused(
    sessions: sessionmaker[Session], document: uuid.UUID, values: dict[str, Any]
) -> None:
    with pytest.raises(IntegrityError):
        add_assessment(sessions, document, **values)


def test_no_model_is_allowed_when_none_was_called(
    sessions: sessionmaker[Session],
) -> None:
    failed = add_document(sessions, status="failed")

    add_assessment(
        sessions, failed, document_status="failed", model=None, prompt_version=None
    )


def test_a_re_run_adds_an_assessment_and_keeps_the_earlier_one(
    sessions: sessionmaker[Session], document: uuid.UUID
) -> None:
    first = add_assessment(sessions, document)
    second = add_assessment(sessions, document)

    assert first != second


@pytest.mark.parametrize("status", ["reported", "partially_reported", "not_found"])
def test_each_status_without_review_is_accepted(
    sessions: sessionmaker[Session], document: uuid.UUID, status: str
) -> None:
    add_item(sessions, add_assessment(sessions, document), status=status)


@pytest.mark.parametrize(
    "reason", ["parse_incomplete", "evidence_unverified", "model_uncertain"]
)
def test_needs_review_is_accepted_with_a_reason(
    sessions: sessionmaker[Session], document: uuid.UUID, reason: str
) -> None:
    add_item(
        sessions,
        add_assessment(sessions, document),
        status="needs_review",
        review_reason=reason,
    )


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({"status": "irreproducible"}, id="invalid status"),
        pytest.param({"status": "needs_review"}, id="review without a reason"),
        pytest.param(
            {"status": "not_found", "review_reason": "parse_incomplete"},
            id="reason on another status",
        ),
        pytest.param(
            {"status": "needs_review", "review_reason": "other"}, id="unknown reason"
        ),
        pytest.param({"item_key": ""}, id="empty key"),
        pytest.param({"explanation": ""}, id="empty explanation"),
    ],
)
def test_an_inconsistent_item_is_refused(
    sessions: sessionmaker[Session], document: uuid.UUID, values: dict[str, Any]
) -> None:
    assessment = add_assessment(sessions, document)

    with pytest.raises(IntegrityError):
        add_item(sessions, assessment, **values)


def test_each_item_appears_once_per_assessment(
    sessions: sessionmaker[Session], document: uuid.UUID
) -> None:
    first = add_assessment(sessions, document)
    add_item(sessions, first)
    add_item(sessions, add_assessment(sessions, document))

    with pytest.raises(IntegrityError):
        add_item(sessions, first)


def test_a_passage_examined_without_evidence_has_no_quote(
    sessions: sessionmaker[Session], document: uuid.UUID
) -> None:
    item = add_item(sessions, add_assessment(sessions, document), status="not_found")
    passage = passage_of(sessions, document)

    with sessions.begin() as session:
        session.add(ReproducibilityItemPassage(item_id=item, passage_id=passage))


def test_a_quote_cannot_be_empty(
    sessions: sessionmaker[Session], document: uuid.UUID
) -> None:
    item = add_item(sessions, add_assessment(sessions, document))
    passage = passage_of(sessions, document)

    with pytest.raises(IntegrityError), sessions.begin() as session:
        session.add(
            ReproducibilityItemPassage(item_id=item, passage_id=passage, quote="")
        )


def test_a_passage_is_linked_once_per_item(
    sessions: sessionmaker[Session], document: uuid.UUID
) -> None:
    item = add_item(sessions, add_assessment(sessions, document))
    passage = passage_of(sessions, document)
    with sessions.begin() as session:
        session.add(ReproducibilityItemPassage(item_id=item, passage_id=passage))

    with pytest.raises(IntegrityError), sessions.begin() as session:
        session.add(ReproducibilityItemPassage(item_id=item, passage_id=passage))


@pytest.mark.parametrize(
    "statement",
    [
        pytest.param("DELETE FROM passages", id="passage with a link"),
        pytest.param("DELETE FROM reproducibility_items", id="item with a link"),
        pytest.param("DELETE FROM reproducibility_assessments", id="assessment"),
        pytest.param("DELETE FROM documents", id="document"),
    ],
)
def test_linked_rows_cannot_be_deleted_from_under_each_other(
    sessions: sessionmaker[Session],
    document: uuid.UUID,
    schema_engine: Engine,
    statement: str,
) -> None:
    item = add_item(sessions, add_assessment(sessions, document))
    with sessions.begin() as session:
        session.add(
            ReproducibilityItemPassage(
                item_id=item, passage_id=passage_of(sessions, document)
            )
        )

    with pytest.raises(DBAPIError), schema_engine.begin() as connection:
        connection.execute(text(statement))


def test_the_labeller_sees_passages_in_reading_order_with_locations(
    sessions: sessionmaker[Session],
) -> None:
    document = add_document(
        sessions,
        {"text": "First.", "section_title": "Intro", "page_start": 1, "page_end": 1},
        "Second.",
    )

    shown = load_paper(sessions, "p1", "A title", document)

    assert (shown.key, shown.title) == ("p1", "A title")
    assert [p.text for p in shown.passages] == ["First.", "Second."]
    assert (shown.passages[0].section, shown.passages[0].page) == ("Intro", 1)
    assert (shown.passages[1].section, shown.passages[1].page) == (None, None)

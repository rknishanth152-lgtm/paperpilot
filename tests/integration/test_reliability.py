"""Failure paths across the whole chain (P6-T4; NFR-REL-001, NFR-REL-002, NFR-PRI-002)."""

import logging
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_answers_api import BODY, ask, client_for, output
from tests.integration.test_ingestion_pipeline import (
    GOOD_TEI,
    FakeParser,
    count,
    get_document,
    ingestion,
    passages_of,
    upload,
)
from tests.integration.test_keyword_retrieval import add_document

from app.models import Document, Paper, Passage
from app.services.ingestion.documents import process_in_background
from app.services.ingestion.grobid import ParserFailure
from app.services.ingestion.pipeline import Ingestion
from app.services.ingestion.recovery import recover_interrupted
from app.services.ingestion.tei import ParsedDocument, ParsedPassage, parse_tei
from app.storage import LocalStorage

SECRET = "UNPUBLISHED-PAPER-SENTENCE"
EXPECTED_PASSAGES = len(parse_tei(GOOD_TEI).passages)


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "storage")


class LosesDatabase:
    """Real sessions until one transaction fails, as a lost connection would."""

    def __init__(self, sessions: sessionmaker[Session], fail_on_begin: int) -> None:
        self._sessions = sessions
        self._fail_on = fail_on_begin
        self._begins = 0

    def __call__(self) -> Session:
        return self._sessions()

    def begin(self) -> Any:
        self._begins += 1
        if self._begins == self._fail_on:
            raise OperationalError("UPDATE", {"text": SECRET}, Exception(SECRET))
        return self._sessions.begin()


def losing(
    sessions: sessionmaker[Session],
    storage: LocalStorage,
    parser: FakeParser,
    fail_on_begin: int,
) -> Ingestion:
    broken: Any = LosesDatabase(sessions, fail_on_begin)
    return Ingestion(broken, storage, parser)


def assert_one_complete_passage_set(
    sessions: sessionmaker[Session], document_id: Any
) -> None:
    ordinals = [p.ordinal for p in passages_of(sessions, document_id)]
    assert ordinals == list(range(EXPECTED_PASSAGES))
    assert count(sessions, Paper) == 1


# --- Database failure during ingestion ----------------------------------------


@pytest.mark.parametrize(
    ("fail_on_begin", "parser_failure", "left_as"),
    [
        pytest.param(1, None, "pending", id="starting"),
        pytest.param(2, None, "processing", id="writing the result"),
        pytest.param(
            2,
            ParserFailure("parser_busy", "busy"),
            "processing",
            id="recording a parser failure",
        ),
    ],
)
def test_a_lost_database_leaves_nothing_half_done_and_can_be_recovered(
    sessions: sessionmaker[Session],
    storage: LocalStorage,
    caplog: pytest.LogCaptureFixture,
    fail_on_begin: int,
    parser_failure: ParserFailure | None,
    left_as: str,
) -> None:
    working = ingestion(sessions, storage, FakeParser(GOOD_TEI))
    document_id = working.register(upload()).document_id
    parser = FakeParser(GOOD_TEI, failure=parser_failure)

    with caplog.at_level(logging.DEBUG):
        process_in_background(
            losing(sessions, storage, parser, fail_on_begin), document_id
        )

    assert get_document(sessions, document_id).status == left_as
    assert passages_of(sessions, document_id) == []
    assert count(sessions, Paper) == 0
    assert SECRET not in caplog.text
    assert str(document_id) in caplog.text
    assert "OperationalError" in caplog.text
    assert [r.levelname for r in caplog.records if "OperationalError" in r.message] == [
        "ERROR"
    ]

    recover_interrupted(sessions)
    assert working.process(document_id) == "parsed"
    assert_one_complete_passage_set(sessions, document_id)


def with_rejected_passage(raw: bytes) -> ParsedDocument:
    parsed = parse_tei(raw)
    bad = ParsedPassage(len(parsed.passages), "body", None, None, None, SECRET, 0, 0)
    return ParsedDocument(**{**parsed.__dict__, "passages": [*parsed.passages, bad]})


def test_a_rejected_write_logs_no_paper_text_and_recovers_to_one_set(
    sessions: sessionmaker[Session],
    storage: LocalStorage,
    caplog: pytest.LogCaptureFixture,
) -> None:
    rejecting = ingestion(
        sessions, storage, FakeParser(GOOD_TEI), with_rejected_passage
    )
    document_id = rejecting.register(upload()).document_id

    with caplog.at_level(logging.DEBUG):
        process_in_background(rejecting, document_id)

    assert SECRET not in caplog.text
    assert "IntegrityError" in caplog.text
    document = get_document(sessions, document_id)
    assert document.status == "processing"
    assert count(sessions, Passage) == 0
    assert count(sessions, Paper) == 0

    assert recover_interrupted(sessions) == [document_id]
    assert get_document(sessions, document_id).failure_reason == "interrupted"
    assert (
        ingestion(sessions, storage, FakeParser(GOOD_TEI)).process(document_id)
        == "parsed"
    )
    assert_one_complete_passage_set(sessions, document_id)


def test_a_document_already_taken_is_skipped_without_an_error(
    sessions: sessionmaker[Session],
    storage: LocalStorage,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pipeline = ingestion(sessions, storage, FakeParser(GOOD_TEI))
    document_id = pipeline.register(upload()).document_id
    pipeline.process(document_id)

    with caplog.at_level(logging.DEBUG):
        process_in_background(pipeline, document_id)

    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert_one_complete_passage_set(sessions, document_id)


def test_database_errors_do_not_carry_the_values_being_written(
    db_engine: Engine,
) -> None:
    with pytest.raises(DBAPIError) as caught, db_engine.connect() as connection:
        connection.execute(
            text("SELECT 1 FROM no_such_table WHERE x = :value"), {"value": SECRET}
        )

    assert SECRET not in str(caught.value)


# --- Parse and storage failures ---------------------------------------------


def test_a_stored_pdf_that_has_gone_missing_is_an_explicit_failure(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    parser = FakeParser(GOOD_TEI)
    pipeline = ingestion(sessions, storage, parser)
    document_id = pipeline.register(upload()).document_id
    storage.delete(get_document(sessions, document_id).storage_key)

    assert pipeline.process(document_id) == "failed"

    document = get_document(sessions, document_id)
    assert document.failure_reason == "storage_error"
    assert parser.received == []
    assert passages_of(sessions, document_id) == []


# --- Repeated identical requests ----------------------------------------------


def stored_state(sessions: sessionmaker[Session]) -> list[Any]:
    with sessions() as session:
        return [
            session.execute(
                select(Passage.id, Passage.text).order_by(Passage.id)
            ).all(),
            session.execute(
                select(Document.id, Document.status).order_by(Document.id)
            ).all(),
            session.execute(select(Paper.id).order_by(Paper.id)).all(),
        ]


def test_the_same_question_twice_gives_the_same_answer_and_stores_nothing(
    sessions: sessionmaker[Session],
) -> None:
    document = add_document(sessions, BODY)
    before = stored_state(sessions)
    client = client_for(sessions, output(), output())

    first = ask(client, document)
    second = ask(client, document)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["validation_status"] == "validated"
    assert stored_state(sessions) == before


# --- Incomplete or missing evidence -------------------------------------------


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_a_document_that_is_not_parsed_gives_no_evidence(
    sessions: sessionmaker[Session], status: str
) -> None:
    document = add_document(sessions, BODY, status=status)

    response = ask(client_for(sessions), document)

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_sufficiency"] == "insufficient"
    assert body["statements"] == []
    assert body["evidence"] == []
    assert body["model"] is None


def test_only_the_parsed_document_in_a_mixed_scope_is_used(
    sessions: sessionmaker[Session],
) -> None:
    parsed = add_document(sessions, BODY)
    failed = add_document(sessions, BODY, status="failed")
    client = client_for(sessions, output())

    body = client.post(
        "/answers",
        json={"question": "glacier", "document_ids": [str(parsed), str(failed)]},
    ).json()

    assert [e["document_id"] for e in body["evidence"]] == [str(parsed)]
    assert len(body["retrieved_passage_ids"]) == 1

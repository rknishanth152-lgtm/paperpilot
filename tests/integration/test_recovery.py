"""Startup recovery of interrupted documents (P3-T7, FR-ING-010, AD-010).

Stale `processing` rows are manufactured directly, as a crash would leave them.
"""

import hashlib
import itertools
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar

from sqlalchemy.orm import Session, sessionmaker
from tests.synthetic import BODY, tei

from app.models import Document, Paper
from app.services.ingestion.pipeline import Ingestion
from app.services.ingestion.recovery import INTERRUPTED_MESSAGE, recover_interrupted
from app.storage import LocalStorage

_n = itertools.count()


def add_document(sessions: sessionmaker[Session], **values: Any) -> uuid.UUID:
    n = next(_n)
    with sessions.begin() as session:
        defaults: dict[str, Any] = {
            "sha256": hashlib.sha256(f"recovery-{n}".encode()).hexdigest(),
            "size_bytes": 10,
            "storage_key": f"pdf/{n}",
        }
        document = Document(**{**defaults, **values})
        session.add(document)
        session.flush()
        return document.id


def get(sessions: sessionmaker[Session], document_id: uuid.UUID) -> Document:
    with sessions() as session:
        document = session.get(Document, document_id)
        assert document is not None
        return document


STARTED = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_processing_documents_become_failed_interrupted(
    sessions: sessionmaker[Session],
) -> None:
    stale = add_document(sessions, status="processing", processing_started_at=STARTED)

    recovered = recover_interrupted(sessions)

    assert recovered == [stale]
    document = get(sessions, stale)
    assert (document.status, document.failure_reason) == ("failed", "interrupted")
    assert document.failure_message == INTERRUPTED_MESSAGE
    assert document.processing_started_at == STARTED  # kept as evidence


def test_other_documents_are_left_alone(sessions: sessionmaker[Session]) -> None:
    with sessions.begin() as session:
        paper = Paper(metadata_source="grobid")
        session.add(paper)
        session.flush()
        paper_id = paper.id
    pending = add_document(sessions)
    failed = add_document(sessions, status="failed", failure_reason="parser_busy")
    parsed = add_document(
        sessions,
        status="parsed",
        paper_id=paper_id,
        parser_name="grobid",
        parser_version="0.9.1",
        tei_storage_key="tei/x",
    )
    stale = add_document(
        sessions,
        status="processing",
        processing_started_at=STARTED + timedelta(hours=1),
    )

    assert recover_interrupted(sessions) == [stale]

    assert get(sessions, pending).status == "pending"
    assert get(sessions, failed).failure_reason == "parser_busy"
    assert get(sessions, parsed).status == "parsed"


def test_several_stale_documents_are_all_recovered(
    sessions: sessionmaker[Session],
) -> None:
    stale = {
        add_document(sessions, status="processing", processing_started_at=STARTED)
        for _ in range(3)
    }

    assert set(recover_interrupted(sessions)) == stale


def test_recovery_is_idempotent(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, status="processing", processing_started_at=STARTED)

    assert len(recover_interrupted(sessions)) == 1
    assert recover_interrupted(sessions) == []


def test_nothing_to_recover(sessions: sessionmaker[Session]) -> None:
    assert recover_interrupted(sessions) == []


def test_recovered_document_can_be_retried(
    sessions: sessionmaker[Session], tmp_path: Path
) -> None:
    """FR-ING-010: '... and may be retried'."""

    class Parser:
        parser_config: ClassVar[dict[str, str]] = {"endpoint": "/fake"}

        def process_fulltext(self, pdf: bytes) -> bytes:
            return tei(body=BODY)

    storage = LocalStorage(tmp_path)
    key = storage.save(b"%PDF-1.4 stale", kind="pdf")
    stale = add_document(
        sessions, status="processing", processing_started_at=STARTED, storage_key=key
    )
    recover_interrupted(sessions)

    assert Ingestion(sessions, storage, Parser()).process(stale) == "parsed"
    assert get(sessions, stale).failure_reason is None

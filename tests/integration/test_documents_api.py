"""Document HTTP API (P3-T8; FR-ING-001, FR-ING-008, FR-ING-009, NFR-SEC-005).

The real routes run against the throwaway database. A fake parser stands in
for GROBID and storage is a temporary folder. TestClient runs background
tasks before it returns, so processing has finished when a request returns.
"""

import hashlib
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.synthetic import BODY, p, section, tei

from app.api.dependencies import get_ingestion, get_sessions
from app.config import Settings, get_settings
from app.main import create_app
from app.models import Document, Passage
from app.services.ingestion.grobid import ParserFailure
from app.services.ingestion.pipeline import Ingestion
from app.storage import LocalStorage, StorageError

PDF = b"%PDF-1.4 synthetic api test document"
MIB = 1024 * 1024


class FakeParser:
    def __init__(self) -> None:
        self.tei_bytes = tei(
            abstract=p("An abstract sentence."),
            body=BODY + section("Methods", p("Second section.", coords=None), n="2"),
        )
        self.failure: ParserFailure | None = None
        self.calls = 0

    @property
    def parser_config(self) -> dict[str, Any]:
        return {"endpoint": "/fake"}

    def process_fulltext(self, pdf: bytes) -> bytes:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return self.tei_bytes


class PdfStorageFails(LocalStorage):
    def save(self, data: bytes, *, kind: str) -> str:
        raise StorageError("file could not be stored (OSError)")


@pytest.fixture
def parser() -> FakeParser:
    return FakeParser()


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path)


@pytest.fixture
def client(
    sessions: sessionmaker[Session], storage: LocalStorage, parser: FakeParser
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, postgres_password="pw", max_upload_mb=1
    )
    app.dependency_overrides[get_sessions] = lambda: sessions
    app.dependency_overrides[get_ingestion] = lambda: Ingestion(
        sessions, storage, parser
    )
    # Not used as a context manager: startup recovery is tested elsewhere.
    return TestClient(app, raise_server_exceptions=False)


def upload(client: TestClient, body: bytes = PDF, **headers: str) -> Any:
    return client.post(
        "/documents",
        content=body,
        headers={"Content-Type": "application/pdf", **headers},
    )


def count(sessions: sessionmaker[Session], model: type[Any]) -> int:
    with sessions() as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def assert_error(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    return dict(body["error"])


# --- Upload ------------------------------------------------------------------


def test_upload_returns_pending_document_then_processes_it(
    client: TestClient, sessions: sessionmaker[Session]
) -> None:
    response = upload(client)

    assert response.status_code == 202
    body = response.json()
    assert body["created"] is True
    assert body["status"] == "pending"
    document_id = body["document_id"]

    status = client.get(f"/documents/{document_id}").json()
    assert status["status"] == "parsed"
    assert status["failure_reason"] is None
    assert count(sessions, Passage) > 0


def test_upload_records_hash_and_size(client: TestClient) -> None:
    body = upload(client).json()

    assert body["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert body["size_bytes"] == len(PDF)


def test_same_file_twice_returns_existing_document(
    client: TestClient, sessions: sessionmaker[Session], parser: FakeParser
) -> None:
    """AC-VS-04: one document, one passage set."""
    first = upload(client).json()
    passages = count(sessions, Passage)

    second = upload(client)

    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["document_id"] == first["document_id"]
    assert second.json()["status"] == "parsed"
    assert count(sessions, Document) == 1
    assert count(sessions, Passage) == passages
    assert parser.calls == 1


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        (b"", 400, "empty_file"),
        (b"hello, this is text renamed to .pdf", 415, "not_pdf"),
        (b"%PDF-" + b"x" * MIB, 413, "file_too_large"),
    ],
)
def test_rejected_uploads_create_nothing(
    client: TestClient,
    sessions: sessionmaker[Session],
    tmp_path: Path,
    body: bytes,
    status: int,
    code: str,
) -> None:
    assert_error(upload(client, body), status, code)
    assert count(sessions, Document) == 0
    assert not list(tmp_path.rglob("*.pdf"))


def test_upload_at_exactly_the_limit_is_accepted(client: TestClient) -> None:
    body = b"%PDF-" + b"x" * (MIB - 5)
    assert len(body) == MIB

    assert upload(client, body).status_code == 202


def test_declared_length_over_the_limit_is_rejected_before_reading(
    client: TestClient, sessions: sessionmaker[Session]
) -> None:
    response = client.post(
        "/documents",
        content=PDF,
        headers={"Content-Type": "application/pdf", "Content-Length": str(MIB + 1)},
    )
    assert_error(response, 413, "file_too_large")
    assert count(sessions, Document) == 0


def test_chunked_upload_over_the_limit_is_rejected(
    client: TestClient, sessions: sessionmaker[Session]
) -> None:
    """No Content-Length: the limit is enforced while reading the stream."""

    def chunks() -> Iterator[bytes]:
        yield b"%PDF-"
        for _ in range(4):
            yield b"x" * (MIB // 2)

    response = client.post("/documents", content=chunks())

    assert "content-length" not in {name.lower() for name in response.request.headers}
    assert_error(response, 413, "file_too_large")
    assert count(sessions, Document) == 0


def test_content_type_is_not_trusted(client: TestClient) -> None:
    """The file type is decided by content, not by the declared media type."""
    assert upload(client, PDF, **{"Content-Type": "text/plain"}).status_code == 202
    assert_error(
        upload(client, b"plain text", **{"Content-Type": "application/pdf"}),
        415,
        "not_pdf",
    )


@pytest.mark.parametrize(
    ("header", "shown"),
    [
        ("R%C3%A9sum%C3%A9%20paper.pdf", "Résumé paper.pdf"),
        ("..%2F..%2Fetc%2Fpasswd.pdf", "passwd.pdf"),
        ("C%3A%5Cusers%5Cme%5Cpaper.pdf", "paper.pdf"),
        ("%00%0A", None),
    ],
)
def test_filename_header_is_display_only(
    client: TestClient, tmp_path: Path, header: str, shown: str | None
) -> None:
    body = upload(client, PDF, **{"X-Filename": header}).json()

    assert body["original_filename"] == shown
    stored = [path.name for path in tmp_path.rglob("*.pdf")]
    assert len(stored) == 1
    assert stored[0] != shown


def test_upload_without_filename(client: TestClient) -> None:
    assert upload(client).json()["original_filename"] is None


def test_storage_failure_creates_no_document(
    client: TestClient,
    sessions: sessionmaker[Session],
    parser: FakeParser,
    tmp_path: Path,
) -> None:
    app: Any = client.app
    broken = PdfStorageFails(tmp_path / "broken")
    app.dependency_overrides[get_ingestion] = lambda: Ingestion(
        sessions, broken, parser
    )

    error = assert_error(upload(client), 500, "storage_error")

    assert "OSError" not in error["message"]
    assert count(sessions, Document) == 0


# --- Status ------------------------------------------------------------------


def test_failed_document_shows_reason_and_explanation_not_internal_message(
    client: TestClient, parser: FakeParser
) -> None:
    parser.failure = ParserFailure(
        "parser_unreachable", "GROBID request failed (ConnectError)"
    )
    document_id = upload(client).json()["document_id"]

    body = client.get(f"/documents/{document_id}").json()

    assert body["status"] == "failed"
    assert body["failure_reason"] == "parser_unreachable"
    assert body["failure_explanation"]
    assert "failure_message" not in body
    assert "ConnectError" not in str(body)


def test_status_of_unknown_document(client: TestClient) -> None:
    assert_error(client.get(f"/documents/{uuid.uuid4()}"), 404, "document_not_found")


def test_malformed_document_id(client: TestClient) -> None:
    error = assert_error(client.get("/documents/not-a-uuid"), 422, "invalid_request")
    assert "details" not in error  # no echo of the input or pydantic internals


# --- Structure ---------------------------------------------------------------


def test_structure_of_parsed_document(client: TestClient) -> None:
    """FR-ING-009: metadata, then passages in order with section and page or null."""
    document_id = upload(client).json()["document_id"]

    body = client.get(f"/documents/{document_id}/structure").json()

    assert body["document_id"] == document_id
    assert body["status"] == "parsed"
    assert body["parser"] == {"name": "grobid", "version": "0.9.1"}
    assert body["page_count"] == 2
    assert body["paper"]["title"] == "A Synthetic Paper"
    assert body["paper"]["authors"] == ["Ada B Example", "Ben Sample"]
    passages = body["passages"]
    assert [item["ordinal"] for item in passages] == list(range(len(passages)))
    assert [item["region"] for item in passages] == ["abstract", "body", "body"]
    assert passages[1]["section_title"] == "Introduction"
    assert passages[1]["section_number"] == "1"
    assert passages[1]["text"] == "A synthetic sentence."
    assert passages[1]["page_start"] == 1
    # No coordinates: the page is unknown, shown as null, never 0 (DR-007).
    assert passages[2]["section_title"] == "Methods"
    assert passages[2]["page_start"] is None
    assert passages[2]["page_end"] is None
    assert set(passages[0]) == {
        "passage_id",
        "ordinal",
        "region",
        "back_type",
        "section_number",
        "section_title",
        "text",
        "page_start",
        "page_end",
    }


def test_structure_of_failed_document_returns_status_and_reason(
    client: TestClient, parser: FakeParser
) -> None:
    parser.failure = ParserFailure("no_text_layer", "GROBID error NO_BLOCKS (HTTP 500)")
    document_id = upload(client).json()["document_id"]

    error = assert_error(
        client.get(f"/documents/{document_id}/structure"), 409, "document_not_parsed"
    )

    assert error["details"] == {
        "status": "failed",
        "failure_reason": "no_text_layer",
    }


def test_structure_of_unknown_document(client: TestClient) -> None:
    assert_error(
        client.get(f"/documents/{uuid.uuid4()}/structure"), 404, "document_not_found"
    )


# --- Retry -------------------------------------------------------------------


def test_failed_document_can_be_retried(
    client: TestClient, sessions: sessionmaker[Session], parser: FakeParser
) -> None:
    parser.failure = ParserFailure("parser_busy", "GROBID returned HTTP 503")
    document_id = upload(client).json()["document_id"]
    parser.failure = None

    response = client.post(f"/documents/{document_id}/retry")

    assert response.status_code == 202
    assert response.json()["document_id"] == document_id
    body = client.get(f"/documents/{document_id}").json()
    assert body["status"] == "parsed"
    assert body["failure_reason"] is None
    assert count(sessions, Document) == 1


def test_parsed_document_cannot_be_retried(
    client: TestClient, sessions: sessionmaker[Session], parser: FakeParser
) -> None:
    document_id = upload(client).json()["document_id"]
    passages = count(sessions, Passage)

    error = assert_error(
        client.post(f"/documents/{document_id}/retry"), 409, "document_not_retryable"
    )

    assert error["details"] == {"status": "parsed"}
    assert parser.calls == 1
    assert count(sessions, Passage) == passages


def test_retry_unknown_document(client: TestClient) -> None:
    assert_error(
        client.post(f"/documents/{uuid.uuid4()}/retry"), 404, "document_not_found"
    )


def test_reupload_of_failed_document_does_not_retry(
    client: TestClient, parser: FakeParser
) -> None:
    """Retrying is explicit (decided P3-T8); a re-upload has no side effect."""
    parser.failure = ParserFailure("parser_busy", "GROBID returned HTTP 503")
    upload(client)

    second = upload(client).json()

    assert second["status"] == "failed"
    assert parser.calls == 1


# --- Unexpected errors -------------------------------------------------------


def test_unexpected_error_hides_internals(
    client: TestClient, sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    class Exploding(FakeParser):
        def process_fulltext(self, pdf: bytes) -> bytes:
            raise RuntimeError("secret C:\\internal\\path postgres_password=pw")

    class ExplodingIngestion(Ingestion):
        def register(self, upload: Any) -> Any:
            raise RuntimeError("secret C:\\internal\\path postgres_password=pw")

    app: Any = client.app
    app.dependency_overrides[get_ingestion] = lambda: ExplodingIngestion(
        sessions, storage, Exploding()
    )

    response = upload(client)

    error = assert_error(response, 500, "internal_error")
    assert "secret" not in response.text
    assert "Traceback" not in response.text
    assert "details" not in error

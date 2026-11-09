"""The list of papers shown in the library (redesign; FR-UI-001). No paper text."""

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_keyword_retrieval import add_document

from app.api.dependencies import get_sessions
from app.main import create_app
from app.models import Paper
from app.services.ingestion.explanations import FAILURE_EXPLANATIONS


def client_for(sessions: sessionmaker[Session]) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_sessions] = lambda: sessions
    return TestClient(app, raise_server_exceptions=False)


def titled(sessions: sessionmaker[Session], title: str | None) -> uuid.UUID:
    with sessions.begin() as session:
        paper = Paper(metadata_source="grobid", title=title)
        session.add(paper)
        session.flush()
        paper_id = paper.id
    return add_document(sessions, "Text.", paper_id=paper_id)


def listing(sessions: sessionmaker[Session]) -> list[dict[str, Any]]:
    response = client_for(sessions).get("/documents")
    assert response.status_code == 200, response.text
    documents: list[dict[str, Any]] = response.json()["documents"]
    return documents


def test_an_empty_library(sessions: sessionmaker[Session]) -> None:
    assert listing(sessions) == []


def test_papers_are_listed_newest_first(sessions: sessionmaker[Session]) -> None:
    first = titled(sessions, "Older")
    second = titled(sessions, "Newer")

    assert [d["document_id"] for d in listing(sessions)] == [str(second), str(first)]


def test_a_parsed_paper_shows_its_title(sessions: sessionmaker[Session]) -> None:
    titled(sessions, "A Study of Ice")

    [row] = listing(sessions)

    assert row["title"] == "A Study of Ice"
    assert row["status"] == "parsed"
    assert row["failure_explanation"] is None
    assert row["created_at"]


def test_a_missing_title_stays_null(sessions: sessionmaker[Session]) -> None:
    titled(sessions, None)

    assert listing(sessions)[0]["title"] is None


def test_every_status_is_listed(sessions: sessionmaker[Session]) -> None:
    for status in ("pending", "processing", "failed"):
        add_document(sessions, status=status)

    rows = listing(sessions)

    assert sorted(r["status"] for r in rows) == ["failed", "pending", "processing"]
    assert all(r["title"] is None for r in rows)


def test_a_failure_is_explained_in_plain_words(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, status="failed")

    assert (
        listing(sessions)[0]["failure_explanation"]
        == FAILURE_EXPLANATIONS["parser_busy"]
    )


def test_the_list_holds_no_paper_text_or_storage_details(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "SECRET passage text.")

    text = client_for(sessions).get("/documents").text

    assert "SECRET" not in text
    assert "storage_key" not in text


def test_no_explanation_uses_internal_terms() -> None:
    for text in FAILURE_EXPLANATIONS.values():
        lowered = text.lower()
        assert "grobid" not in lowered
        assert "parser" not in lowered
        assert "tei" not in lowered.split()

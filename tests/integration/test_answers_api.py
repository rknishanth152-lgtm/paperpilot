"""The answers route (P5-T11; FR-QA-001, FR-UI-003, NFR-SEC-005). Uses the fake model."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_keyword_retrieval import add_document, add_paper
from tests.unit.test_answer_call import limits

from app.api.dependencies import get_answering
from app.config import Settings, get_settings
from app.main import create_app
from app.services.answering.pipeline import Answering
from app.services.llm import (
    FakeModel,
    ModelAuthenticationError,
    ModelError,
    ModelRateLimitError,
    ModelRefusedError,
    ModelTimeoutError,
    ModelTruncatedError,
    ModelUnavailableError,
)

BODY = "Glaciers retreated quickly in the last decade."


def output(alias: str = "P1", quote: str | None = "retreated quickly") -> str:
    return json.dumps(
        {
            "statements": [
                {
                    "text": "Ice retreated.",
                    "citations": [{"alias": alias, "quote": quote}],
                }
            ],
            "evidence_sufficiency": "sufficient",
            "limitations": None,
        }
    )


def client_for(
    sessions: sessionmaker[Session], *script: Any, **limit_values: Any
) -> TestClient:
    app = create_app()
    model = FakeModel(list(script), model_name="fake-api")
    app.dependency_overrides[get_answering] = lambda: Answering(
        sessions, model, limits(**limit_values)
    )
    return TestClient(app, raise_server_exceptions=False)


def ask(client: TestClient, document_id: Any, question: str = "glacier") -> Any:
    return client.post(
        "/answers", json={"question": question, "document_ids": [str(document_id)]}
    )


def assert_error(response: Any, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]


def test_a_validated_answer(sessions: sessionmaker[Session]) -> None:
    document_id = add_document(
        sessions,
        {"text": BODY, "section_title": "Results", "page_start": 2, "page_end": 2},
    )

    response = ask(client_for(sessions, output()), document_id)

    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "validated"
    assert body["evidence_sufficiency"] == "sufficient"
    assert body["claim_support"] == "not_evaluated"
    assert body["model"] == "fake-api"
    assert body["retrieval_method"] == "keyword_full_text"
    citation = body["statements"][0]["citations"][0]
    assert (citation["alias"], citation["valid"], citation["reason"]) == (
        "P1",
        True,
        None,
    )
    assert body["evidence"][0]["section"] == "Results"
    assert body["evidence"][0]["page_start"] == 2
    assert body["evidence"][0]["text"] == BODY


def test_a_failed_validation_is_a_normal_response_marked_failed(
    sessions: sessionmaker[Session],
) -> None:
    document_id = add_document(sessions, BODY)

    response = ask(client_for(sessions, output("P9", None)), document_id)

    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "failed"
    assert body["evidence"] == []
    assert body["statements"][0]["citations"][0]["reason"] == "passage_not_found"


def test_nothing_retrieved_is_insufficient_without_a_model_call(
    sessions: sessionmaker[Session],
) -> None:
    document_id = add_document(sessions, BODY)

    response = ask(client_for(sessions), document_id, question="volcano")

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_sufficiency"] == "insufficient"
    assert body["model"] is None


def test_paper_scope_is_accepted(sessions: sessionmaker[Session]) -> None:
    document_id = add_document(sessions, BODY)
    client = client_for(sessions, output())
    paper_id = ask(client, document_id).json()["evidence"][0]["paper_id"]

    follow_up = client_for(sessions, output()).post(
        "/answers", json={"question": "glacier", "paper_ids": [paper_id]}
    )

    assert follow_up.json()["validation_status"] == "validated"


@pytest.mark.parametrize(
    "body",
    [
        {"question": "glacier"},
        {"question": "glacier", "document_ids": []},
        {"question": "glacier", "paper_ids": []},
        {"question": "glacier", "document_ids": [], "paper_ids": []},
    ],
)
def test_a_scope_is_required(
    sessions: sessionmaker[Session], body: dict[str, Any]
) -> None:
    """FR-QA-001 answers about selected papers."""
    assert_error(
        client_for(sessions).post("/answers", json=body), 422, "invalid_request"
    )


@pytest.mark.parametrize(
    "body",
    [
        {"document_ids": ["0190a1b2-0000-7000-8000-000000000001"]},
        {"question": 7, "document_ids": ["0190a1b2-0000-7000-8000-000000000001"]},
        {"question": "glacier", "document_ids": ["not-a-uuid"]},
        {
            "question": "glacier",
            "document_ids": ["0190a1b2-0000-7000-8000-000000000001"],
            "extra": 1,
        },
    ],
)
def test_invalid_requests_are_rejected(
    sessions: sessionmaker[Session], body: dict[str, Any]
) -> None:
    assert_error(
        client_for(sessions).post("/answers", json=body), 422, "invalid_request"
    )


def test_an_over_long_question_is_refused(sessions: sessionmaker[Session]) -> None:
    document_id = add_document(sessions, BODY)

    response = ask(
        client_for(sessions, max_query_chars=5), document_id, "too long a question"
    )

    assert_error(response, 422, "query_too_long")
    assert "too long a question" not in response.text


def test_malformed_output_is_a_structured_error(
    sessions: sessionmaker[Session],
) -> None:
    document_id = add_document(sessions, BODY)

    response = ask(client_for(sessions, "SECRET", "SECRET"), document_id)

    assert_error(response, 502, "malformed_model_output")
    assert "SECRET" not in response.text


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (ModelTimeoutError, 504, "model_timeout"),
        (ModelRateLimitError, 429, "model_rate_limited"),
        (ModelAuthenticationError, 502, "model_authentication_failed"),
        (ModelUnavailableError, 502, "model_unavailable"),
        (ModelRefusedError, 502, "model_refused"),
        (ModelTruncatedError, 502, "model_output_truncated"),
    ],
)
def test_provider_failures_are_structured_errors(
    sessions: sessionmaker[Session],
    error: type[ModelError],
    status: int,
    code: str,
) -> None:
    document_id = add_document(sessions, BODY)

    assert_error(ask(client_for(sessions, error()), document_id), status, code)


def test_no_model_configured_is_explained() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, postgres_password="pw"
    )
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/answers",
        json={
            "question": "glacier",
            "document_ids": ["0190a1b2-0000-7000-8000-000000000001"],
        },
    )

    assert_error(response, 503, "model_not_configured")


@pytest.mark.parametrize("scope_by", ["document_ids", "paper_ids"])
def test_the_scope_reaches_retrieval(
    sessions: sessionmaker[Session], scope_by: str
) -> None:
    paper = add_paper(sessions)
    wanted = add_document(sessions, "Glaciers in the wanted paper.", paper_id=paper)
    add_document(sessions, "Glaciers in another paper.")
    scope = {"document_ids": wanted, "paper_ids": paper}[scope_by]

    response = client_for(sessions, output("P1", None)).post(
        "/answers", json={"question": "glacier", scope_by: [str(scope)]}
    )

    body = response.json()
    assert len(body["retrieved_passage_ids"]) == 1
    assert body["evidence"][0]["document_id"] == str(wanted)

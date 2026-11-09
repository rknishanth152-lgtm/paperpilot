"""The checklist routes and their wording (R7; FR-REP-004, NFR-SEC-005). Fake model."""

import json
import re
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_answers_api import assert_error
from tests.integration.test_keyword_retrieval import add_document
from tests.unit.test_answer_call import limits

from app.api.dependencies import get_assessor, get_sessions
from app.config import Settings, get_settings
from app.main import create_app
from app.models import ReproducibilityAssessment
from app.services.llm import FakeModel, ModelRateLimitError
from app.services.reproducibility.assessment import Assessor
from app.services.reproducibility.checklist import CHECKLIST
from app.services.retrieval.selection import KeywordRetriever

BODY = "The paper says the data are at example.org and the code is public."
QUOTE = {"alias": "P1", "quote": "the data are at example.org"}
KEYS = [item.key for item in CHECKLIST]
NOT_FOUND_LABEL = "Not found in the material examined"


def reply(status: str = "not_found", *evidence: dict[str, str]) -> str:
    return json.dumps(
        {"status": status, "explanation": "Explained.", "evidence": list(evidence)}
    )


def script(*first: Any) -> list[Any]:
    return [*first, *[reply()] * (len(CHECKLIST) - len(first))]


def client_for(sessions: sessionmaker[Session], *replies: Any) -> TestClient:
    app = create_app()
    model = FakeModel(list(replies), model_name="fake-api")
    app.dependency_overrides[get_assessor] = lambda: Assessor(
        sessions, model, limits(), KeywordRetriever(sessions)
    )
    app.dependency_overrides[get_sessions] = lambda: sessions
    return TestClient(app, raise_server_exceptions=False)


def url(document: Any) -> str:
    return f"/documents/{document}/assessment"


def located(sessions: sessionmaker[Session]) -> uuid.UUID:
    return add_document(
        sessions,
        {"text": BODY, "section_title": "Data", "page_start": 2, "page_end": 3},
    )


def test_running_returns_every_item_in_checklist_order(
    sessions: sessionmaker[Session],
) -> None:
    document = located(sessions)
    client = client_for(sessions, *script(reply("reported", QUOTE)))

    response = client.post(url(document))

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["key"] for item in body["items"]] == KEYS
    assert body["document_id"] == str(document)
    assert body["checklist_version"] == "checklist-v1"
    assert body["document_status"] == "parsed"
    assert body["model"] == "fake-api"
    assert body["prompt_version"] == "reproducibility-v1"
    assert body["retrieval_method"] == "keyword_full_text"
    assert body["created_at"]
    assert body["items"][0]["title"] == CHECKLIST[0].title
    assert body["items"][0]["question"] == CHECKLIST[0].question


def test_evidence_shows_the_quote_and_the_stored_location(
    sessions: sessionmaker[Session],
) -> None:
    document = located(sessions)
    client = client_for(sessions, *script(reply("reported", QUOTE)))

    item = client.post(url(document)).json()["items"][0]

    assert item["status"] == "reported"
    assert item["status_label"] == "Stated in the paper"
    assert item["explanation"] == "Explained."
    assert item["passages_examined"] == 1
    [evidence] = item["evidence"]
    assert evidence["quote"] == QUOTE["quote"]
    assert (evidence["section"], evidence["page_start"], evidence["page_end"]) == (
        "Data",
        2,
        3,
    )
    assert evidence["text"] == BODY
    assert evidence["passage_id"]


def test_an_unknown_location_stays_null(sessions: sessionmaker[Session]) -> None:
    document = add_document(sessions, BODY)
    client = client_for(sessions, *script(reply("reported", QUOTE)))

    [evidence] = client.post(url(document)).json()["items"][0]["evidence"]

    assert (evidence["section"], evidence["page_start"], evidence["page_end"]) == (
        None,
        None,
        None,
    )


def test_not_found_always_says_it_is_about_the_material_examined(
    sessions: sessionmaker[Session],
) -> None:
    document = located(sessions)
    client = client_for(sessions, *script())

    item = client.post(url(document)).json()["items"][0]

    assert item["status"] == "not_found"
    assert item["status_label"] == NOT_FOUND_LABEL
    assert "does not mean" in item["status_description"]
    assert item["evidence"] == []
    assert item["passages_examined"] == 1


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_a_document_not_parsed_says_so_and_never_not_found(
    sessions: sessionmaker[Session], status: str
) -> None:
    document = add_document(sessions, status=status)

    body = client_for(sessions).post(url(document)).json()

    assert body["document_status"] == status
    assert body["model"] is None
    for item in body["items"]:
        assert item["status"] == "needs_review"
        assert item["review_reason"] == "parse_incomplete"
        assert item["status_label"] == "Needs your review"
        assert "not fully processed" in item["status_description"]
        assert item["passages_examined"] == 0


@pytest.mark.parametrize(
    ("first", "reason", "text"),
    [
        pytest.param(
            reply("reported"), "evidence_unverified", "could not be verified", id="unv"
        ),
        pytest.param(
            reply("needs_review"), "model_uncertain", "did not settle", id="unc"
        ),
    ],
)
def test_each_review_reason_has_its_own_plain_description(
    sessions: sessionmaker[Session], first: str, reason: str, text: str
) -> None:
    document = located(sessions)
    client = client_for(sessions, *script(first))

    item = client.post(url(document)).json()["items"][0]

    assert (item["status"], item["review_reason"]) == ("needs_review", reason)
    assert text in item["status_description"]


def test_no_response_holds_a_score_or_verdict(
    sessions: sessionmaker[Session],
) -> None:
    document = located(sessions)
    client = client_for(
        sessions, *script(reply("reported", QUOTE), reply("needs_review"))
    )

    # The prompt's own version name is an identifier, not a statement.
    text = client.post(url(document)).text.lower().replace("reproducibility-v1", "")

    assert not re.search(r"reproducib|irreproduc|score|grade|verdict", text)


def test_the_latest_assessment_is_returned(sessions: sessionmaker[Session]) -> None:
    document = located(sessions)
    client = client_for(
        sessions, *script(reply("needs_review")), *script(reply("reported", QUOTE))
    )
    client.post(url(document))
    latest = client.post(url(document)).json()

    response = client.get(url(document))

    assert response.status_code == 200
    assert response.json() == latest
    assert response.json()["items"][0]["status"] == "reported"


def test_reading_runs_nothing(sessions: sessionmaker[Session]) -> None:
    document = located(sessions)

    assert_error(client_for(sessions).get(url(document)), 404, "assessment_not_found")

    with sessions() as session:
        assert session.scalars(select(ReproducibilityAssessment)).all() == []


@pytest.mark.parametrize("method", ["get", "post"])
def test_an_unknown_document(sessions: sessionmaker[Session], method: str) -> None:
    response = getattr(client_for(sessions), method)(url(uuid.uuid4()))

    assert_error(response, 404, "document_not_found")


def test_an_invalid_id_is_a_structured_error(sessions: sessionmaker[Session]) -> None:
    assert client_for(sessions).get(url("not-a-uuid")).status_code == 422


def test_a_provider_failure_is_explicit_and_stores_nothing(
    sessions: sessionmaker[Session],
) -> None:
    document = located(sessions)
    client = client_for(sessions, reply(), ModelRateLimitError())

    assert_error(client.post(url(document)), 429, "model_rate_limited")

    assert_error(client.get(url(document)), 404, "assessment_not_found")


def test_malformed_output_is_explicit(sessions: sessionmaker[Session]) -> None:
    document = located(sessions)
    client = client_for(sessions, "SECRET bad", "SECRET bad")

    response = client.post(url(document))

    assert_error(response, 502, "malformed_model_output")
    assert "SECRET" not in response.text


def test_no_configured_model_is_explicit(sessions: sessionmaker[Session]) -> None:
    document = located(sessions)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, postgres_password="x"
    )
    client = TestClient(app, raise_server_exceptions=False)

    assert_error(client.post(url(document)), 503, "model_not_configured")

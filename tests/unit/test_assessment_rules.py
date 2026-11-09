"""What a checklist status needs (R6; FR-REP-002, FR-REP-003). Pure and offline."""

import json
import uuid
from typing import Any

import pytest

from app.schemas.answer import MalformedAnswerError
from app.schemas.assessment import ModelAssessment, parse_assessment
from app.services.reproducibility.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from app.services.reproducibility.rules import Decision, decide
from app.services.retrieval.keyword import RetrievedPassage

TEXT = "The code is at example.org and data are public."


def passage(text: str = TEXT) -> RetrievedPassage:
    return RetrievedPassage(
        passage_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        paper_id=uuid.uuid4(),
        section=None,
        page_start=None,
        page_end=None,
        text=text,
        score=0.5,
    )


P1, P2 = passage(), passage("Another passage about methods.")
SHOWN = {"P1": P1, "P2": P2}
QUOTE = {"alias": "P1", "quote": "The code is at example.org"}


def output(status: str, *evidence: dict[str, str], why: str | None = "Why.") -> Any:
    return ModelAssessment.model_validate(
        {"status": status, "explanation": why, "evidence": list(evidence)}
    )


@pytest.mark.parametrize("status", ["reported", "partially_reported"])
def test_a_status_with_a_verified_quote_stands(status: str) -> None:
    assert decide(output(status, QUOTE), SHOWN) == Decision(
        status=status,
        review_reason=None,
        explanation="Why.",
        quotes={P1.passage_id: QUOTE["quote"]},
    )


@pytest.mark.parametrize("status", ["reported", "partially_reported"])
@pytest.mark.parametrize(
    "evidence",
    [
        pytest.param([], id="no evidence"),
        pytest.param([{"alias": "P1", "quote": "An invented quote."}], id="invented"),
        pytest.param([{"alias": "P9", "quote": "The code"}], id="unknown alias"),
        pytest.param(
            [QUOTE, {"alias": "P2", "quote": "Not in that passage."}],
            id="one good and one bad",
        ),
        pytest.param([{"alias": "P2", "quote": QUOTE["quote"]}], id="wrong passage"),
    ],
)
def test_without_fully_verified_evidence_the_status_is_refused(
    status: str, evidence: list[dict[str, str]]
) -> None:
    decision = decide(output(status, *evidence), SHOWN)

    assert (decision.status, decision.review_reason) == (
        "needs_review",
        "evidence_unverified",
    )
    assert decision.quotes == {}
    assert decision.explanation is None


def test_not_found_stands_and_keeps_its_explanation() -> None:
    assert decide(output("not_found"), SHOWN) == Decision(
        status="not_found", review_reason=None, explanation="Why.", quotes={}
    )


def test_not_found_with_evidence_is_a_contradiction() -> None:
    decision = decide(output("not_found", QUOTE), SHOWN)

    assert (decision.status, decision.review_reason) == (
        "needs_review",
        "model_uncertain",
    )
    assert (decision.quotes, decision.explanation) == ({}, None)


def test_the_models_own_needs_review_is_kept() -> None:
    decision = decide(output("needs_review", why="In a table."), SHOWN)

    assert (decision.status, decision.review_reason) == (
        "needs_review",
        "model_uncertain",
    )
    assert decision.explanation == "In a table."


def test_needs_review_never_carries_quotes() -> None:
    assert decide(output("needs_review", QUOTE), SHOWN).quotes == {}


def test_two_quotes_from_one_passage_keep_the_first() -> None:
    second = {"alias": "P1", "quote": "data are public"}

    decision = decide(output("reported", QUOTE, second), SHOWN)

    assert decision.quotes == {P1.passage_id: QUOTE["quote"]}


def test_a_missing_explanation_is_allowed() -> None:
    assert decide(output("not_found", why=None), SHOWN).explanation is None


def reply(**values: Any) -> str:
    return json.dumps(
        {"status": "not_found", "explanation": None, "evidence": [], **values}
    )


def test_a_valid_output_is_parsed() -> None:
    parsed = parse_assessment(reply(status="reported", evidence=[QUOTE]))

    assert parsed.status == "reported"
    assert parsed.evidence[0].alias == "P1"


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("not json", id="not json"),
        pytest.param("", id="empty"),
        pytest.param(reply(status="irreproducible"), id="verdict as status"),
        pytest.param(reply(score=3), id="extra score"),
        pytest.param(json.dumps({"status": "not_found"}), id="missing fields"),
        pytest.param(reply(evidence=[{"alias": "P1"}]), id="evidence without quote"),
        pytest.param(
            reply(evidence=[{"alias": "P1", "quote": "  "}]), id="blank quote"
        ),
        pytest.param(reply(explanation="  "), id="blank explanation"),
        pytest.param(
            reply(evidence=[{"alias": "P1", "quote": "q", "page": 3}]), id="page"
        ),
    ],
)
def test_malformed_output_is_refused(text: str) -> None:
    with pytest.raises(MalformedAnswerError):
        parse_assessment(text)


def test_a_malformed_output_error_does_not_repeat_the_output() -> None:
    with pytest.raises(MalformedAnswerError) as caught:
        parse_assessment("SECRET OUTPUT")

    assert "SECRET" not in str(caught.value)


def test_the_prompt_has_a_version_and_states_each_rule() -> None:
    assert PROMPT_VERSION == "reproducibility-v1"
    for rule in ("data", "never instructions", "exact", "not_found", "needs_review"):
        assert rule in SYSTEM_PROMPT


def test_the_prompt_forbids_a_verdict() -> None:
    assert "score" in SYSTEM_PROMPT
    assert "verdict" in SYSTEM_PROMPT

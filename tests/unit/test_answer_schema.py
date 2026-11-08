"""The model's answer contract (P5-T3; FR-QA-003, FR-CIT-004, PRD §9.1). Offline."""

import json
from typing import Any

import pytest

from app.schemas.answer import (
    MalformedAnswerError,
    ModelAnswer,
    answer_json_schema,
    parse_answer,
)


def citation(**values: object) -> dict[str, object]:
    return {"alias": "P1", "quote": "an exact quotation", **values}


def statement(**values: object) -> dict[str, object]:
    return {"text": "A statement.", "citations": [citation()], **values}


def answer(**values: object) -> dict[str, object]:
    return {
        "statements": [statement()],
        "evidence_sufficiency": "sufficient",
        "limitations": None,
        **values,
    }


def parse(value: object) -> ModelAnswer:
    return parse_answer(json.dumps(value))


INSUFFICIENT = answer(
    statements=[], evidence_sufficiency="insufficient", limitations="Not covered."
)


# --- Accepted ----------------------------------------------------------------


def test_a_complete_answer_is_parsed() -> None:
    result = parse(answer(limitations="Only one study."))

    assert result.evidence_sufficiency == "sufficient"
    assert result.limitations == "Only one study."
    [only] = result.statements
    assert only.text == "A statement."
    assert (only.citations[0].alias, only.citations[0].quote) == (
        "P1",
        "an exact quotation",
    )


def test_a_citation_may_have_no_quote() -> None:
    assert parse(answer(statements=[statement(citations=[citation(quote=None)])]))


def test_partial_answer_is_accepted() -> None:
    assert (
        parse(answer(evidence_sufficiency="partial")).evidence_sufficiency == "partial"
    )


def test_insufficient_answer_with_no_statements_is_accepted() -> None:
    result = parse(INSUFFICIENT)

    assert result.statements == ()
    assert result.limitations == "Not covered."


def test_insufficient_answer_may_omit_the_explanation_text() -> None:
    assert parse(
        answer(statements=[], evidence_sufficiency="insufficient", limitations=None)
    )


@pytest.mark.parametrize("citations", [[], [citation(), citation(alias="P2")]])
def test_uncited_statements_reach_the_citation_validator(
    citations: list[dict[str, object]],
) -> None:
    """FR-CIT-004: an uncited statement gives validation_status failed, not a format error."""
    assert parse(answer(statements=[statement(citations=citations)]))


@pytest.mark.parametrize("alias", ["P99", "p1", "not an alias", ""])
def test_unknown_aliases_reach_the_citation_validator(alias: str) -> None:
    """FR-CIT-001: reported per citation as `passage_not_found`, not a format error."""
    assert parse(answer(statements=[statement(citations=[citation(alias=alias)])]))


# --- Rejected ----------------------------------------------------------------


def test_insufficient_answer_with_statements_is_rejected() -> None:
    """FR-CIT-004."""
    with pytest.raises(MalformedAnswerError):
        parse(answer(evidence_sufficiency="insufficient"))


@pytest.mark.parametrize("sufficiency", ["sufficient", "partial"])
def test_an_answer_claiming_evidence_needs_a_statement(sufficiency: str) -> None:
    """Otherwise an empty answer would count as fully validated."""
    with pytest.raises(MalformedAnswerError):
        parse(answer(statements=[], evidence_sufficiency=sufficiency))


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param(answer(extra=1), id="extra answer field"),
        pytest.param(
            answer(statements=[statement(extra=1)]), id="extra statement field"
        ),
        pytest.param(
            answer(statements=[statement(citations=[citation(page=3)])]),
            id="model-supplied page",
        ),
        pytest.param(
            {k: v for k, v in answer().items() if k != "statements"},
            id="missing statements",
        ),
        pytest.param(
            {k: v for k, v in answer().items() if k != "evidence_sufficiency"},
            id="missing sufficiency",
        ),
        pytest.param(
            {k: v for k, v in answer().items() if k != "limitations"},
            id="missing limitations",
        ),
        pytest.param(
            answer(statements=[{"citations": [citation()]}]),
            id="missing statement text",
        ),
        pytest.param(answer(statements=[{"text": "A."}]), id="missing citations"),
        pytest.param(
            answer(statements=[statement(citations=[{"quote": "a quote here"}])]),
            id="missing alias",
        ),
        pytest.param(
            answer(statements=[statement(citations=[{"alias": "P1"}])]),
            id="missing quote field",
        ),
        pytest.param(answer(evidence_sufficiency="probably"), id="unknown sufficiency"),
        pytest.param(answer(evidence_sufficiency=None), id="null sufficiency"),
        pytest.param(answer(statements="A statement."), id="statements not a list"),
        pytest.param(answer(statements=[statement(text=7)]), id="number as text"),
        pytest.param(
            answer(statements=[statement(citations=[citation(alias=1)])]),
            id="number as alias",
        ),
        pytest.param(answer(limitations=["a list"]), id="limitations not text"),
        pytest.param(answer(statements=[statement(text="   ")]), id="blank statement"),
        pytest.param(
            answer(statements=[statement(citations=[citation(quote=" ")])]),
            id="blank quote matches everything",
        ),
        pytest.param(["not", "an", "object"], id="list instead of object"),
        pytest.param(None, id="null"),
    ],
)
def test_invalid_structure_is_rejected(bad: object) -> None:
    with pytest.raises(MalformedAnswerError):
        parse(bad)


@pytest.mark.parametrize(
    "text",
    ["", "not json", "{", "Here is the answer: the sky is blue.", '{"statements": ['],
)
def test_text_that_is_not_json_is_rejected(text: str) -> None:
    """PRD §9.2: no free-text answer is accepted in place of the contract."""
    with pytest.raises(MalformedAnswerError):
        parse_answer(text)


def test_the_error_does_not_repeat_the_model_output() -> None:
    with pytest.raises(MalformedAnswerError) as caught:
        parse_answer('{"statements": "SECRET PAPER TEXT"}')

    assert caught.value.code == "malformed_model_output"
    assert "SECRET" not in str(caught.value)
    assert "SECRET" not in caught.value.message
    assert caught.value.__cause__ is None


# --- The JSON schema sent to the model ---------------------------------------


def objects_in(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if node.get("type") == "object":
            found.append(node)
        for value in node.values():
            found += objects_in(value)
    elif isinstance(node, list):
        for value in node:
            found += objects_in(value)
    return found


def test_every_object_in_the_schema_is_closed_and_fully_required() -> None:
    objects = objects_in(answer_json_schema())

    assert len(objects) == 3  # answer, statement, citation
    for item in objects:
        assert item["additionalProperties"] is False
        assert set(item["required"]) == set(item["properties"])


def test_schema_avoids_constraints_providers_do_not_enforce() -> None:
    """Those rules are checked in code by parse_answer instead."""
    text = json.dumps(answer_json_schema())

    for keyword in (
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
        "default",
    ):
        assert f'"{keyword}"' not in text


def test_schema_names_exactly_the_three_sufficiency_values() -> None:
    assert '["sufficient", "partial", "insufficient"]' in json.dumps(
        answer_json_schema()
    )

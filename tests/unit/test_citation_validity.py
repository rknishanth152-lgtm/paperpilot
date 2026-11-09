"""The citation reference-validity rate over saved answers (P6-T2, FR-EVL-003)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from tests.evaluation.citation_validity import (
    citation_validity,
    validity_record,
    write_validity,
)
from tests.evaluation.code_state import CodeState
from tests.evaluation.run_answers import summarize

NO_REASONS = {
    "passage_not_found": 0,
    "not_in_context": 0,
    "wrong_paper": 0,
    "quote_mismatch": 0,
}
STATE = CodeState(revision="abcdef1234567", clean=True)
RUN_AT = datetime(2026, 11, 9, 8, 30, 5, tzinfo=UTC)


def good() -> dict[str, Any]:
    return {"alias": "P1", "quote": None, "valid": True, "reason": None}


def bad(reason: str | None) -> dict[str, Any]:
    return {"alias": "P9", "quote": None, "valid": False, "reason": reason}


def answer(
    *statements: list[dict[str, Any]], status: str = "validated"
) -> dict[str, Any]:
    return {
        "error": None,
        "model_calls": 1,
        "input_tokens": 0,
        "output_tokens": 0,
        "model_seconds": 0.0,
        "answerable": True,
        "validation_status": status,
        "statements": [
            {"text": "A claim.", "citations": citations} for citations in statements
        ],
    }


def errored() -> dict[str, Any]:
    return {
        "error": "model_timeout",
        "model_calls": 1,
        "input_tokens": 0,
        "output_tokens": 0,
        "model_seconds": 0.0,
        "answerable": True,
    }


def test_every_valid_citation_gives_a_full_rate() -> None:
    result = citation_validity([answer([good(), good()], [good()])])

    assert result["citations"] == {"valid": 3, "total": 3, "rate": 1.0}
    assert result["failure_reasons"] == NO_REASONS
    assert result["answers_with_statements"] == {
        "validated": 1,
        "total": 1,
        "rate": 1.0,
    }


def test_each_failure_is_counted_under_its_own_reason() -> None:
    result = citation_validity(
        [
            answer(
                [good(), bad("quote_mismatch")],
                [bad("quote_mismatch"), bad("wrong_paper")],
                status="failed",
            ),
            answer([bad("passage_not_found"), bad("not_in_context")], status="failed"),
        ]
    )

    assert result["citations"] == {"valid": 1, "total": 6, "rate": 0.1667}
    assert result["failure_reasons"] == {
        "passage_not_found": 1,
        "not_in_context": 1,
        "wrong_paper": 1,
        "quote_mismatch": 2,
    }
    assert result["answers_with_statements"] == {
        "validated": 0,
        "total": 2,
        "rate": 0.0,
    }


def test_a_statement_with_no_citation_is_counted_and_fails_its_answer() -> None:
    result = citation_validity([answer([good()], [], status="failed")])

    assert result["uncited_statements"] == 1
    assert result["citations"] == {"valid": 1, "total": 1, "rate": 1.0}
    assert result["answers_with_statements"]["validated"] == 0


def test_an_answer_with_no_statements_does_not_inflate_the_rate() -> None:
    result = citation_validity(
        [answer([bad("wrong_paper")], status="failed"), answer()]
    )

    assert result["answers_with_statements"] == {
        "validated": 0,
        "total": 1,
        "rate": 0.0,
    }
    assert result["answers_without_statements"] == 1


def test_a_model_error_is_counted_separately() -> None:
    result = citation_validity([answer([good()]), errored()])

    assert result["answers_not_produced"] == 1
    assert result["answers_with_statements"]["total"] == 1
    assert result["answers_without_statements"] == 0


def test_with_nothing_to_measure_the_rate_is_absent_not_zero() -> None:
    result = citation_validity([answer(), errored()])

    assert result["citations"] == {"valid": 0, "total": 0, "rate": None}
    assert result["answers_with_statements"] == {
        "validated": 0,
        "total": 0,
        "rate": None,
    }


@pytest.mark.parametrize(
    "citation",
    [
        bad("a_reason_nobody_defined"),
        bad(None),
        {"alias": "P1", "quote": None, "valid": True, "reason": "wrong_paper"},
    ],
)
def test_a_citation_that_makes_no_sense_stops_the_count(
    citation: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="citation"):
        citation_validity([answer([citation], status="failed")])


def test_new_runs_carry_the_rate_in_their_summary() -> None:
    summary = summarize([answer([good(), bad("wrong_paper")], status="failed")], "m")

    assert summary["citation_validity"]["citations"] == {
        "valid": 1,
        "total": 2,
        "rate": 0.5,
    }


SOURCE: dict[str, Any] = {
    "requested_model": "gemini-3.5-flash-lite",
    "prompt_version": "answer-v1",
    "code_revision": "1111111aaaaaaa",
    "working_tree_clean": False,
    "stopped_early": "model_rate_limited",
    "questions": [answer([good()])],
}


def record() -> dict[str, Any]:
    return validity_record(
        source=SOURCE,
        source_name="answers-x.json",
        source_sha256="b" * 64,
        state=STATE,
        run_at=RUN_AT,
    )


def test_a_saved_rate_says_exactly_what_it_was_computed_from() -> None:
    saved = record()

    assert saved["run_at"] == "2026-11-09T08:30:05+00:00"
    assert saved["code_revision"] == "abcdef1234567"
    assert saved["working_tree_clean"] is True
    assert saved["source"] == {
        "file": "answers-x.json",
        "sha256": "b" * 64,
        "model": "gemini-3.5-flash-lite",
        "prompt_version": "answer-v1",
        "code_revision": "1111111aaaaaaa",
        "working_tree_clean": False,
        "stopped_early": "model_rate_limited",
        "answers": 1,
    }
    assert saved["result"] == citation_validity(SOURCE["questions"])


def test_a_saved_rate_states_that_it_is_not_claim_support() -> None:
    assert "does not show that a passage supports a statement" in record()["scope"]


def test_a_rate_is_saved_under_a_dated_name_and_never_overwritten(
    tmp_path: Path,
) -> None:
    path = write_validity(record(), tmp_path)

    assert path.name == "citation-validity-20261109T083005Z-abcdef1-bbbbbbbb.json"
    assert json.loads(path.read_text(encoding="utf-8")) == record()
    with pytest.raises(FileExistsError):
        write_validity(record(), tmp_path)

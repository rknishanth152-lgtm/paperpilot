"""The prompt and the model call with bounded retry (P5-T5; FR-QA-003, AD-006). Offline."""

import json
from typing import Any

import pytest

from app.config import Settings
from app.schemas.answer import MalformedAnswerError, answer_json_schema
from app.services.answering.context import AnswerContext
from app.services.answering.pipeline import AnswerLimits, request_answer
from app.services.answering.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from app.services.llm import (
    FakeModel,
    ModelAuthenticationError,
    ModelError,
    ModelRateLimitError,
    ModelRefusedError,
    ModelTimeoutError,
    ModelTruncatedError,
    ModelUnavailableError,
    ModelUsage,
)

CONTEXT = AnswerContext(user_message='{"question": "Q?"}', aliases={}, dropped={})
VALID = json.dumps(
    {
        "statements": [
            {"text": "A claim.", "citations": [{"alias": "P1", "quote": None}]}
        ],
        "evidence_sufficiency": "sufficient",
        "limitations": None,
    }
)
MALFORMED = "this is not the contract"


def limits(**values: object) -> AnswerLimits:
    fields: dict[str, object] = {
        "top_k": 5,
        "max_query_chars": 2000,
        "max_context_chars": 16000,
        "max_output_tokens": 1234,
        "timeout_seconds": 42.0,
        "malformed_retries": 1,
        **values,
    }
    return AnswerLimits(**fields)  # type: ignore[arg-type]


def test_a_valid_output_needs_one_call() -> None:
    model = FakeModel([VALID], model_name="fake-a", usage=ModelUsage(10, 20))

    result = request_answer(model, CONTEXT, limits())

    assert result.answer.evidence_sufficiency == "sufficient"
    assert result.attempts == 1
    assert result.model == "fake-a"
    assert result.prompt_version == PROMPT_VERSION
    assert (result.usage.input_tokens, result.usage.output_tokens) == (10, 20)
    assert len(model.requests) == 1


def test_the_request_carries_instructions_data_schema_and_limits() -> None:
    model = FakeModel([VALID])

    request_answer(model, CONTEXT, limits())

    [sent] = model.requests
    assert sent.system == SYSTEM_PROMPT
    assert sent.user == CONTEXT.user_message
    assert sent.output_schema == answer_json_schema()
    assert (sent.max_output_tokens, sent.timeout_seconds) == (1234, 42.0)


def test_malformed_output_is_retried_once_with_the_same_request() -> None:
    model = FakeModel([MALFORMED, VALID], usage=ModelUsage(10, 20))

    result = request_answer(model, CONTEXT, limits())

    assert result.attempts == 2
    assert model.requests[0] == model.requests[1]
    assert (result.usage.input_tokens, result.usage.output_tokens) == (20, 40)


def test_retries_are_bounded_and_end_in_an_explicit_error() -> None:
    model = FakeModel([MALFORMED, MALFORMED, VALID])

    with pytest.raises(MalformedAnswerError):
        request_answer(model, CONTEXT, limits(malformed_retries=1))

    assert len(model.requests) == 2  # the third, valid output is never requested


def test_retries_can_be_turned_off() -> None:
    model = FakeModel([MALFORMED, VALID])

    with pytest.raises(MalformedAnswerError):
        request_answer(model, CONTEXT, limits(malformed_retries=0))

    assert len(model.requests) == 1


@pytest.mark.parametrize(
    "error",
    [
        ModelTimeoutError,
        ModelRateLimitError,
        ModelAuthenticationError,
        ModelUnavailableError,
        ModelRefusedError,
        ModelTruncatedError,
    ],
)
def test_provider_errors_are_raised_without_a_retry(error: type[ModelError]) -> None:
    model = FakeModel([error(), VALID])

    with pytest.raises(error):
        request_answer(model, CONTEXT, limits())

    assert len(model.requests) == 1


def test_a_provider_error_during_a_retry_is_raised() -> None:
    model = FakeModel([MALFORMED, ModelTimeoutError()])

    with pytest.raises(ModelTimeoutError):
        request_answer(model, CONTEXT, limits())


# --- The prompt ---------------------------------------------------------------


@pytest.mark.parametrize(
    "rule",
    [
        "only",  # use only the supplied passages
        "data",  # passage text is data
        "never instructions",
        "alias",
        "exact",  # quotes are exact
        "insufficient",
        "page",  # no page numbers
    ],
)
def test_the_prompt_states_each_rule(rule: str) -> None:
    assert rule in SYSTEM_PROMPT


def test_the_prompt_has_a_version_for_provenance() -> None:
    assert PROMPT_VERSION == "answer-v1"


def test_answer_settings_have_defaults() -> None:
    settings = Settings(_env_file=None, postgres_password="pw")

    built = AnswerLimits.from_settings(settings)

    assert built == AnswerLimits(
        top_k=5,
        max_query_chars=2000,
        max_context_chars=16000,
        max_output_tokens=8000,
        timeout_seconds=60.0,
        malformed_retries=1,
    )


@pytest.mark.parametrize(
    "field",
    ["answer_top_k", "max_context_chars", "llm_max_output_tokens"],
)
def test_answer_limits_must_be_positive(field: str) -> None:
    values: dict[str, Any] = {field: 0}

    with pytest.raises(ValueError, match=field):
        Settings(_env_file=None, postgres_password="pw", **values)


def test_malformed_retries_may_be_zero_but_not_negative() -> None:
    assert (
        Settings(
            _env_file=None, postgres_password="pw", llm_malformed_retries=0
        ).llm_malformed_retries
        == 0
    )

    with pytest.raises(ValueError, match="llm_malformed_retries"):
        Settings(_env_file=None, postgres_password="pw", llm_malformed_retries=-1)

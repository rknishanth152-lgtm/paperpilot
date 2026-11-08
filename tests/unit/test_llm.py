"""The model interface and its fake (P5-T2; FR-QA-005, AD-011). Offline."""

import pytest

from app.config import Settings
from app.services.llm import (
    FakeModel,
    FakeModelExhaustedError,
    LanguageModel,
    ModelAuthenticationError,
    ModelError,
    ModelRateLimitError,
    ModelRefusedError,
    ModelRequest,
    ModelTimeoutError,
    ModelTruncatedError,
    ModelUnavailableError,
    ModelUsage,
)

ALL_ERRORS = [
    (ModelTimeoutError, "model_timeout"),
    (ModelRateLimitError, "model_rate_limited"),
    (ModelAuthenticationError, "model_authentication_failed"),
    (ModelUnavailableError, "model_unavailable"),
    (ModelRefusedError, "model_refused"),
    (ModelTruncatedError, "model_output_truncated"),
]


def request(**values: object) -> ModelRequest:
    fields: dict[str, object] = {
        "system": "Instructions.",
        "user": "A question.",
        "output_schema": {"type": "object"},
        "max_output_tokens": 500,
        "timeout_seconds": 30.0,
        **values,
    }
    return ModelRequest(**fields)  # type: ignore[arg-type]


def test_fake_returns_scripted_outputs_in_order() -> None:
    model = FakeModel(["first", "second"])

    assert model.generate(request()).text == "first"
    assert model.generate(request()).text == "second"


def test_fake_records_each_request_unchanged() -> None:
    model = FakeModel(["ok"])
    sent = request(user="The exact prompt.", timeout_seconds=7.5)

    model.generate(sent)

    assert model.requests == [sent]


def test_response_reports_model_and_usage() -> None:
    model = FakeModel(["ok"], model_name="fake-x", usage=ModelUsage(11, 22))

    response = model.generate(request())

    assert response.model == "fake-x"
    assert (response.usage.input_tokens, response.usage.output_tokens) == (11, 22)


@pytest.mark.parametrize("text", ["not json", "{", "", '{"extra": 1}'])
def test_malformed_output_is_passed_through_for_the_caller_to_reject(
    text: str,
) -> None:
    """Model output is untrusted; the interface neither repairs nor judges it."""
    assert FakeModel([text]).generate(request()).text == text


@pytest.mark.parametrize(("error_type", "code"), ALL_ERRORS)
def test_scripted_errors_are_raised(error_type: type[ModelError], code: str) -> None:
    model = FakeModel([error_type()])

    with pytest.raises(error_type) as caught:
        model.generate(request())

    assert caught.value.code == code


def test_a_scripted_error_does_not_stop_later_outputs() -> None:
    model = FakeModel([ModelTimeoutError(), "after the timeout"])

    with pytest.raises(ModelTimeoutError):
        model.generate(request())

    assert model.generate(request()).text == "after the timeout"
    assert len(model.requests) == 2


def test_running_out_of_outputs_never_invents_one() -> None:
    model = FakeModel(["only one"])
    model.generate(request())

    with pytest.raises(FakeModelExhaustedError):
        model.generate(request())


@pytest.mark.parametrize(("error_type", "code"), ALL_ERRORS)
def test_errors_are_specific_and_plain(error_type: type[ModelError], code: str) -> None:
    error = error_type()

    assert isinstance(error, ModelError)
    assert error.code == code
    assert error.message.endswith(".")
    assert "Traceback" not in error.message


def test_error_codes_are_unique() -> None:
    assert len({code for _, code in ALL_ERRORS}) == len(ALL_ERRORS)


@pytest.mark.parametrize(
    "values",
    [
        {"max_output_tokens": 0},
        {"max_output_tokens": -1},
        {"timeout_seconds": 0},
        {"timeout_seconds": -1.0},
    ],
)
def test_request_limits_must_be_positive(values: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        request(**values)


def test_fake_satisfies_the_interface() -> None:
    model: LanguageModel = FakeModel(["ok"], model_name="fake-y")

    assert model.model_name == "fake-y"


def test_timeout_setting_has_a_default_and_must_be_positive() -> None:
    assert Settings(_env_file=None, postgres_password="pw").llm_timeout_seconds == 60.0

    with pytest.raises(ValueError, match="llm_timeout_seconds"):
        Settings(_env_file=None, postgres_password="pw", llm_timeout_seconds=0)

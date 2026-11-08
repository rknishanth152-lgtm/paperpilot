"""The Anthropic adapter against a stubbed HTTP layer (P5-T12; FR-QA-005). Offline.

The real SDK runs; only the network is replaced, so request shape and error
handling are exercised without an API key or any cost.
"""

import json
from collections.abc import Callable
from typing import Any

import anthropic
import httpx2
import pytest

from app.config import Settings
from app.services.llm import (
    LanguageModel,
    ModelAuthenticationError,
    ModelError,
    ModelNotConfiguredError,
    ModelRateLimitError,
    ModelRefusedError,
    ModelRequest,
    ModelTimeoutError,
    ModelTruncatedError,
    ModelUnavailableError,
)
from app.services.llm_anthropic import AnthropicModel, build_language_model

SCHEMA = {"type": "object", "additionalProperties": False}
KEY = "test-key-not-real"
Handler = Callable[[httpx2.Request], httpx2.Response]


def request(**values: Any) -> ModelRequest:
    fields: dict[str, Any] = {
        "system": "Instructions.",
        "user": '{"question": "Q?"}',
        "output_schema": SCHEMA,
        "max_output_tokens": 500,
        "timeout_seconds": 42.0,
        **values,
    }
    return ModelRequest(**fields)


def reply(
    *blocks: dict[str, Any],
    stop_reason: str = "end_turn",
    model: str = "claude-haiku-5-5",
) -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": list(blocks) or [{"type": "text", "text": '{"ok": true}'}],
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 11, "output_tokens": 22},
        },
    )


def model_with(handler: Handler) -> AnthropicModel:
    client = anthropic.Anthropic(
        api_key=KEY,
        max_retries=0,
        http_client=anthropic.DefaultHttpxClient(
            transport=httpx2.MockTransport(handler)
        ),
    )
    return AnthropicModel(model="claude-haiku-5-5", client=client)


def error_body(status: int, kind: str) -> httpx2.Response:
    return httpx2.Response(
        status,
        json={
            "type": "error",
            "error": {"type": kind, "message": "SECRET provider detail"},
        },
    )


def test_the_request_is_built_from_the_model_request() -> None:
    seen: list[httpx2.Request] = []

    def handler(sent: httpx2.Request) -> httpx2.Response:
        seen.append(sent)
        return reply()

    model_with(handler).generate(request())

    [sent] = seen
    body = json.loads(sent.content)
    assert body["model"] == "claude-haiku-5-5"
    assert body["max_tokens"] == 500
    assert body["system"] == "Instructions."
    assert body["messages"] == [{"role": "user", "content": '{"question": "Q?"}'}]
    assert body["output_config"]["format"] == {"type": "json_schema", "schema": SCHEMA}
    assert KEY in sent.headers.get("authorization", sent.headers.get("x-api-key", ""))
    assert sent.extensions["timeout"]["read"] == 42.0


def test_a_response_gives_text_model_and_usage() -> None:
    response = model_with(lambda _: reply(model="claude-haiku-5-5")).generate(request())

    assert response.text == '{"ok": true}'
    assert response.model == "claude-haiku-5-5"
    assert (response.usage.input_tokens, response.usage.output_tokens) == (11, 22)


def test_thinking_blocks_are_skipped() -> None:
    blocks = (
        {"type": "thinking", "thinking": "", "signature": "x"},
        {"type": "text", "text": "the answer"},
    )

    assert model_with(lambda _: reply(*blocks)).generate(request()).text == "the answer"


def test_a_response_without_text_is_empty_so_the_caller_rejects_it() -> None:
    blocks = ({"type": "thinking", "thinking": "", "signature": "x"},)

    assert model_with(lambda _: reply(*blocks)).generate(request()).text == ""


@pytest.mark.parametrize(
    ("status", "kind", "error"),
    [
        (401, "authentication_error", ModelAuthenticationError),
        (403, "permission_error", ModelAuthenticationError),
        (429, "rate_limit_error", ModelRateLimitError),
        (500, "api_error", ModelUnavailableError),
        (529, "overloaded_error", ModelUnavailableError),
        (400, "invalid_request_error", ModelUnavailableError),
        (404, "not_found_error", ModelUnavailableError),
    ],
)
def test_provider_status_codes_become_specific_errors(
    status: int, kind: str, error: type[ModelError]
) -> None:
    with pytest.raises(error) as caught:
        model_with(lambda _: error_body(status, kind)).generate(request())

    assert "SECRET" not in str(caught.value)
    assert "SECRET" not in caught.value.message
    assert caught.value.__cause__ is None


def test_a_timeout_is_a_model_timeout() -> None:
    def handler(sent: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow", request=sent)

    with pytest.raises(ModelTimeoutError):
        model_with(handler).generate(request())


def test_a_connection_failure_is_unavailable() -> None:
    def handler(sent: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("no route", request=sent)

    with pytest.raises(ModelUnavailableError):
        model_with(handler).generate(request())


@pytest.mark.parametrize(
    ("stop_reason", "error"),
    [("refusal", ModelRefusedError), ("max_tokens", ModelTruncatedError)],
)
def test_a_response_that_did_not_finish_is_an_error(
    stop_reason: str, error: type[ModelError]
) -> None:
    with pytest.raises(error):
        model_with(lambda _: reply(stop_reason=stop_reason)).generate(request())


def test_the_real_client_does_not_retry_on_its_own() -> None:
    """One call must mean one call, for cost and for a meaningful timeout."""
    settings = configured()

    model = build_language_model(settings)

    assert isinstance(model, AnthropicModel)
    assert model.client.max_retries == 0


# --- Choosing the model -------------------------------------------------------


def configured(**values: Any) -> Settings:
    fields: dict[str, Any] = {
        "llm_provider": "anthropic",
        "llm_model": "claude-haiku-5-5",
        "llm_api_key": KEY,
        **values,
    }
    return Settings(_env_file=None, postgres_password="pw", **fields)


def test_a_configured_provider_builds_its_model() -> None:
    model: LanguageModel = build_language_model(configured())

    assert model.model_name == "claude-haiku-5-5"


@pytest.mark.parametrize(
    "values",
    [
        {"llm_provider": None},
        {"llm_model": None},
        {"llm_api_key": None},
        {"llm_provider": "somebody-else"},
    ],
)
def test_incomplete_configuration_is_explained(values: dict[str, Any]) -> None:
    with pytest.raises(ModelNotConfiguredError):
        build_language_model(configured(**values))

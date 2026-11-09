"""The Gemini adapter against a stubbed HTTP layer (P5-T12; FR-QA-005). Offline."""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.schemas.answer import answer_json_schema
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
from app.services.llm_factory import build_language_model
from app.services.llm_gemini import GeminiModel, to_gemini_schema

KEY = "test-key-not-real"
BASE = "https://gemini.test"
SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}}
Handler = Callable[[httpx.Request], httpx.Response]


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
    *steps: dict[str, Any], status: str = "completed", **extra: Any
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "i1",
            "status": status,
            "model": "gemini-3.8-flash",
            "steps": list(steps)
            or [
                {
                    "type": "model_output",
                    "content": [{"type": "text", "text": '{"ok": true}'}],
                }
            ],
            "usage": {
                "total_tokens": 66,
                "total_input_tokens": 11,
                "total_output_tokens": 22,
                "total_thought_tokens": 33,
            },
            **extra,
        },
    )


def model_with(handler: Handler) -> GeminiModel:
    return GeminiModel(
        model="gemini-3.8-flash",
        api_key=KEY,
        base_url=BASE,
        transport=httpx.MockTransport(handler),
    )


def test_the_request_is_built_from_the_model_request() -> None:
    seen: list[httpx.Request] = []

    def handler(sent: httpx.Request) -> httpx.Response:
        seen.append(sent)
        return reply()

    model_with(handler).generate(request())

    [sent] = seen
    assert sent.method == "POST"
    assert str(sent.url) == f"{BASE}/v1beta/interactions"
    assert sent.headers["x-goog-api-key"] == KEY
    assert KEY not in str(sent.url)
    assert sent.extensions["timeout"]["read"] == 42.0
    assert json.loads(sent.content) == {
        "model": "gemini-3.8-flash",
        "system_instruction": "Instructions.",
        "input": '{"question": "Q?"}',
        "store": False,
        "generation_config": {"max_output_tokens": 500},
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": SCHEMA,
        },
    }


def test_the_schema_sent_is_the_converted_one() -> None:
    seen: list[httpx.Request] = []

    def handler(sent: httpx.Request) -> httpx.Response:
        seen.append(sent)
        return reply()

    model_with(handler).generate(request(output_schema=answer_json_schema()))

    sent_schema = json.loads(seen[0].content)["response_format"]["schema"]
    assert sent_schema == to_gemini_schema(answer_json_schema())
    assert "$defs" not in sent_schema


def test_a_response_gives_text_model_and_usage_including_thinking() -> None:
    response = model_with(lambda _: reply()).generate(request())

    assert response.text == '{"ok": true}'
    assert response.model == "gemini-3.8-flash"
    assert response.usage.input_tokens == 11
    assert response.usage.output_tokens == 55  # output plus thinking, as billed


def test_thought_steps_are_skipped_and_text_is_joined() -> None:
    steps = (
        {
            "type": "thought",
            "signature": "x",
            "content": [{"type": "text", "text": "private reasoning"}],
        },
        {
            "type": "model_output",
            "content": [
                {"type": "text", "text": "one "},
                {"type": "text", "text": "two"},
            ],
        },
    )

    assert model_with(lambda _: reply(*steps)).generate(request()).text == "one two"


def test_a_response_without_text_is_empty_so_the_caller_rejects_it() -> None:
    steps = ({"type": "thought", "signature": "x"},)

    assert model_with(lambda _: reply(*steps)).generate(request()).text == ""


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, ModelAuthenticationError),
        (403, ModelAuthenticationError),
        (429, ModelRateLimitError),
        (504, ModelTimeoutError),
        (400, ModelUnavailableError),
        (402, ModelUnavailableError),
        (404, ModelUnavailableError),
        (500, ModelUnavailableError),
        (503, ModelUnavailableError),
    ],
)
def test_status_codes_become_specific_errors(
    status: int, error: type[ModelError]
) -> None:
    body = {"error": {"code": "x", "message": "SECRET provider detail"}}

    with pytest.raises(error) as caught:
        model_with(lambda _: httpx.Response(status, json=body)).generate(request())

    assert "SECRET" not in str(caught.value)
    assert caught.value.__cause__ is None


def test_a_timeout_is_a_model_timeout() -> None:
    def handler(sent: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=sent)

    with pytest.raises(ModelTimeoutError):
        model_with(handler).generate(request())


def test_a_connection_failure_is_unavailable() -> None:
    def handler(sent: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=sent)

    with pytest.raises(ModelUnavailableError):
        model_with(handler).generate(request())


def test_an_unreadable_success_response_is_unavailable() -> None:
    with pytest.raises(ModelUnavailableError):
        model_with(lambda _: httpx.Response(200, content=b"not json")).generate(
            request()
        )


def test_a_success_response_of_the_wrong_shape_is_unavailable() -> None:
    with pytest.raises(ModelUnavailableError):
        model_with(lambda _: httpx.Response(200, json=[1, 2])).generate(request())


def test_an_incomplete_response_is_truncated() -> None:
    with pytest.raises(ModelTruncatedError):
        model_with(lambda _: reply(status="incomplete")).generate(request())


@pytest.mark.parametrize("code", ["safety", "recitation", "prohibited_content", "spii"])
def test_a_blocked_generation_is_a_refusal(code: str) -> None:
    failed = reply(status="failed", errors=[{"code": code, "message": "SECRET"}])

    with pytest.raises(ModelRefusedError):
        model_with(lambda _: failed).generate(request())


@pytest.mark.parametrize(
    "status", ["failed", "cancelled", "in_progress", "requires_action"]
)
def test_any_other_status_never_becomes_an_answer(status: str) -> None:
    with pytest.raises(ModelUnavailableError):
        model_with(lambda _: reply(status=status)).generate(request())


# --- The schema sent to Gemini ------------------------------------------------


def walk(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        found.append(node)
        for value in node.values():
            found += walk(value)
    elif isinstance(node, list):
        for value in node:
            found += walk(value)
    return found


def test_references_are_inlined_and_nothing_unsupported_remains() -> None:
    converted = to_gemini_schema(answer_json_schema())

    nodes = walk(converted)
    assert not any({"$ref", "$defs", "anyOf", "title"} & set(node) for node in nodes)


def test_nullable_fields_use_a_type_list() -> None:
    converted = to_gemini_schema(answer_json_schema())

    assert converted["properties"]["limitations"]["type"] == ["string", "null"]
    citation = converted["properties"]["statements"]["items"]["properties"][
        "citations"
    ]["items"]
    assert citation["properties"]["quote"]["type"] == ["string", "null"]
    assert citation["properties"]["alias"]["type"] == "string"


def test_structure_and_enum_are_kept() -> None:
    converted = to_gemini_schema(answer_json_schema())

    assert set(converted["required"]) == {
        "statements",
        "evidence_sufficiency",
        "limitations",
    }
    assert converted["additionalProperties"] is False
    assert converted["properties"]["evidence_sufficiency"]["enum"] == [
        "sufficient",
        "partial",
        "insufficient",
    ]


def test_a_nested_definition_is_expanded_in_place() -> None:
    schema = {
        "$defs": {"B": {"type": "object", "properties": {"x": {"type": "string"}}}},
        "type": "array",
        "items": {"$ref": "#/$defs/B"},
    }

    assert to_gemini_schema(schema) == {
        "type": "array",
        "items": {"type": "object", "properties": {"x": {"type": "string"}}},
    }


# --- Choosing the model -------------------------------------------------------


def configured(**values: Any) -> Settings:
    fields: dict[str, Any] = {
        "llm_provider": "gemini",
        "llm_model": "gemini-3.8-flash",
        "llm_api_key": KEY,
        **values,
    }
    return Settings(_env_file=None, postgres_password="pw", **fields)


def test_gemini_is_built_when_configured() -> None:
    model: LanguageModel = build_language_model(configured())

    assert isinstance(model, GeminiModel)
    assert model.model_name == "gemini-3.8-flash"


@pytest.mark.parametrize("values", [{"llm_model": None}, {"llm_api_key": None}])
def test_incomplete_gemini_configuration_is_explained(values: dict[str, Any]) -> None:
    with pytest.raises(ModelNotConfiguredError):
        build_language_model(configured(**values))

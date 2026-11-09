"""The Gemini implementation of `LanguageModel` (P5-T12; OQ-011, FR-QA-005).

Uses Google's Interactions REST API over httpx, so it adds no dependency.
Requests are sent with `store: false`. On Google's free tier, content is still
used to improve Google's products and human reviewers may read it, so use the
free tier only with open-access papers (NFR-PRI-001, progress.md §6.13).

Every failure becomes a specific `ModelError` with no provider text attached.
Google's documentation does not say how a blocked generation is reported. A
`failed` status naming a block code is treated as a refusal, and any other
unexpected outcome as unavailable, so it can never turn into an answer.
"""

from collections.abc import Mapping
from typing import Any

import httpx

from app.services.llm import (
    ModelAuthenticationError,
    ModelError,
    ModelRateLimitError,
    ModelRefusedError,
    ModelRequest,
    ModelResponse,
    ModelTimeoutError,
    ModelTruncatedError,
    ModelUnavailableError,
    ModelUsage,
)

_PATH = "/v1beta/interactions"
_API_REVISION = "2026-05-20"
_BLOCK_CODES = frozenset(
    {
        "safety",
        "recitation",
        "language",
        "prohibited_content",
        "spii",
        "blocklist",
        "content_blocked",
    }
)
_STATUS_ERRORS: dict[int, type[ModelError]] = {
    401: ModelAuthenticationError,
    403: ModelAuthenticationError,
    429: ModelRateLimitError,
    504: ModelTimeoutError,
}


def to_gemini_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Inline `$ref`s, write nullable fields as a type list, drop titles.

    Gemini documents nullable types only as `"type": ["string", "null"]`, and
    its support for `$defs` is only partly stated.
    """
    definitions: Mapping[str, Any] = schema.get("$defs", {})

    def convert(node: Any) -> Any:
        if isinstance(node, list):
            return [convert(item) for item in node]
        if not isinstance(node, Mapping):
            return node
        if "$ref" in node:
            return convert(definitions[node["$ref"].rsplit("/", 1)[-1]])
        if "anyOf" in node:
            kept = [branch for branch in node["anyOf"] if branch != {"type": "null"}]
            if len(kept) == 1 and len(node["anyOf"]) == 2:
                return {**convert(kept[0]), "type": [kept[0]["type"], "null"]}
        converted: dict[str, Any] = {}
        for key, value in node.items():
            if key == "$defs" or (key == "title" and isinstance(value, str)):
                continue
            if key == "properties":
                # Field names here are data: a field may be called "title".
                converted[key] = {name: convert(item) for name, item in value.items()}
            else:
                converted[key] = convert(value)
        return converted

    result: dict[str, Any] = convert(schema)
    return result


class GeminiModel:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._url = f"{base_url.rstrip('/')}{_PATH}"
        self._transport = transport

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, request: ModelRequest) -> ModelResponse:
        body = {
            "model": self._model,
            "system_instruction": request.system,
            "input": request.user,
            "store": False,
            "generation_config": {"max_output_tokens": request.max_output_tokens},
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": to_gemini_schema(request.output_schema),
            },
        }
        headers = {"x-goog-api-key": self._api_key, "Api-Revision": _API_REVISION}
        try:
            with httpx.Client(
                transport=self._transport, timeout=request.timeout_seconds
            ) as client:
                response = client.post(self._url, json=body, headers=headers)
        except httpx.TimeoutException:
            raise ModelTimeoutError() from None
        except httpx.TransportError:
            raise ModelUnavailableError() from None

        if response.status_code != 200:
            raise _STATUS_ERRORS.get(response.status_code, ModelUnavailableError)()
        return self._read(response)

    def _read(self, response: httpx.Response) -> ModelResponse:
        try:
            data = response.json()
            status = data["status"]
            usage = data["usage"]
            steps = data.get("steps", [])
            codes = {str(error.get("code")) for error in data.get("errors", [])}
            text = "".join(
                part["text"]
                for step in steps
                if step.get("type") == "model_output"
                for part in step.get("content", [])
                if part.get("type") == "text"
            )
            input_tokens = int(usage["total_input_tokens"])
            output_tokens = int(usage["total_output_tokens"])
            thinking_tokens = int(usage.get("total_thought_tokens", 0))
            model = str(data.get("model", self._model))
        except ValueError, KeyError, TypeError, AttributeError:
            raise ModelUnavailableError() from None

        if status == "incomplete":
            raise ModelTruncatedError()
        if status == "failed" and codes & _BLOCK_CODES:
            raise ModelRefusedError()
        if status != "completed":
            raise ModelUnavailableError()
        return ModelResponse(
            text=text,
            model=model,
            usage=ModelUsage(input_tokens, output_tokens + thinking_tokens),
        )

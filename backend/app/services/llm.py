"""The one interface to language models, and a fake for tests (P5-T2).

FR-QA-005, AD-011. Answering and later extraction depend on `LanguageModel`,
never on a provider's SDK. Every provider failure is one specific `ModelError`,
so a failure can never turn into an invented answer.

Output is returned as raw text and is untrusted: callers validate it against
their own schema (CLAUDE.md §6).
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol


class ModelError(Exception):
    """A model call failed. `code` is stable; `message` is for people."""

    code: ClassVar[str]
    message: ClassVar[str]

    def __init__(self) -> None:
        super().__init__(self.code)


class ModelTimeoutError(ModelError):
    code = "model_timeout"
    message = "The AI model took too long to respond."


class ModelRateLimitError(ModelError):
    code = "model_rate_limited"
    message = "The AI model's rate limit was reached. Try again shortly."


class ModelAuthenticationError(ModelError):
    code = "model_authentication_failed"
    message = "The AI model rejected the configured API key."


class ModelUnavailableError(ModelError):
    code = "model_unavailable"
    message = "The AI model could not be reached."


class ModelRefusedError(ModelError):
    code = "model_refused"
    message = "The AI model declined to answer this request."


class ModelTruncatedError(ModelError):
    code = "model_output_truncated"
    message = "The AI model's response was cut off before it finished."


class FakeModelExhaustedError(RuntimeError):
    """A test asked the fake for more outputs than it scripted."""


@dataclass(frozen=True)
class ModelRequest:
    """One model call. The output must follow `output_schema` (JSON Schema)."""

    system: str
    user: str
    output_schema: Mapping[str, Any]
    max_output_tokens: int
    timeout_seconds: float

    def __post_init__(self) -> None:
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model: str
    usage: ModelUsage


_NO_USAGE = ModelUsage(0, 0)


class LanguageModel(Protocol):
    @property
    def model_name(self) -> str: ...

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Return the raw output, or raise a `ModelError`."""
        ...


class FakeModel:
    """Plays back scripted outputs and errors, and records every request.

    Deterministic and offline, so every test can force a chosen output,
    including malformed ones (NFR-TST-002).
    """

    def __init__(
        self,
        script: Iterable[str | ModelError],
        *,
        model_name: str = "fake-model",
        usage: ModelUsage = _NO_USAGE,
    ) -> None:
        self._script = list(script)
        self._model_name = model_name
        self._usage = usage
        self.requests: list[ModelRequest] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if not self._script:
            raise FakeModelExhaustedError("the fake model has no scripted output left")
        step = self._script.pop(0)
        if isinstance(step, ModelError):
            raise step
        return ModelResponse(text=step, model=self._model_name, usage=self._usage)

"""The Anthropic implementation of `LanguageModel` (P5-T12; OQ-011, FR-QA-005).

The only module that imports the provider's SDK. Every failure becomes a
specific `ModelError` with no provider text attached, and the SDK's automatic
retries are off, so one call is one billed request and the configured timeout
is the real limit.
"""

import logging

import anthropic

from app.config import Settings
from app.services.llm import (
    LanguageModel,
    ModelAuthenticationError,
    ModelNotConfiguredError,
    ModelRateLimitError,
    ModelRefusedError,
    ModelRequest,
    ModelResponse,
    ModelTimeoutError,
    ModelTruncatedError,
    ModelUnavailableError,
    ModelUsage,
)

logger = logging.getLogger(__name__)


class AnthropicModel:
    def __init__(self, *, model: str, client: anthropic.Anthropic) -> None:
        self._model = model
        self.client = client

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, request: ModelRequest) -> ModelResponse:
        try:
            response = self.client.with_options(
                timeout=request.timeout_seconds
            ).messages.create(
                model=self._model,
                max_tokens=request.max_output_tokens,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": dict(request.output_schema),
                    }
                },
            )
        except anthropic.APITimeoutError:
            raise ModelTimeoutError() from None
        except anthropic.RateLimitError:
            raise ModelRateLimitError() from None
        except anthropic.AuthenticationError, anthropic.PermissionDeniedError:
            raise ModelAuthenticationError() from None
        except anthropic.APIStatusError as error:
            logger.warning("anthropic request failed status=%d", error.status_code)
            raise ModelUnavailableError() from None
        except anthropic.APIConnectionError:
            raise ModelUnavailableError() from None

        if response.stop_reason == "refusal":
            raise ModelRefusedError()
        if response.stop_reason == "max_tokens":
            raise ModelTruncatedError()
        text = next((b.text for b in response.content if b.type == "text"), "")
        return ModelResponse(
            text=text,
            model=response.model,
            usage=ModelUsage(response.usage.input_tokens, response.usage.output_tokens),
        )


def build_language_model(settings: Settings) -> LanguageModel:
    """The configured model, or `ModelNotConfiguredError`."""
    key = settings.llm_api_key
    if settings.llm_provider != "anthropic" or not settings.llm_model or key is None:
        raise ModelNotConfiguredError()
    client = anthropic.Anthropic(api_key=key.get_secret_value(), max_retries=0)
    return AnthropicModel(model=settings.llm_model, client=client)

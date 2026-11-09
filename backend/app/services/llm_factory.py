"""Chooses the configured language model (OQ-011, AD-011)."""

import anthropic

from app.config import Settings
from app.services.llm import LanguageModel, ModelNotConfiguredError
from app.services.llm_anthropic import AnthropicModel
from app.services.llm_gemini import GeminiModel


def build_language_model(settings: Settings) -> LanguageModel:
    """The configured model, or `ModelNotConfiguredError`."""
    key = settings.llm_api_key
    if not settings.llm_model or key is None:
        raise ModelNotConfiguredError()
    if settings.llm_provider == "gemini":
        return GeminiModel(
            model=settings.llm_model,
            api_key=key.get_secret_value(),
            base_url=str(settings.gemini_base_url),
        )
    if settings.llm_provider == "anthropic":
        client = anthropic.Anthropic(api_key=key.get_secret_value(), max_retries=0)
        return AnthropicModel(model=settings.llm_model, client=client)
    raise ModelNotConfiguredError()

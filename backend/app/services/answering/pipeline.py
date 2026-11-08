"""One retrieval, one model call (P5-T5; FR-QA-001, FR-QA-003, AD-006). No agent loop.

Retry policy for malformed output: the identical request is sent again, up to
`malformed_retries` more times (default 1), then `MalformedAnswerError`. Nothing
about the failure is fed back to the model, and retrieval is not repeated.
Provider errors are not retried here: each is raised as its own `ModelError`.

If there is nothing to show the model, it is not called, and the answer is
`insufficient` (FR-QA-004). An `insufficient` answer from the model is kept as
it is.

Citations are not checked here; that is the validator's job (P5-T7).

Logs carry counts only, never the question or paper text (NFR-PRI-002).
"""

import logging
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.schemas.answer import (
    MalformedAnswerError,
    ModelAnswer,
    answer_json_schema,
    parse_answer,
)
from app.services.answering.context import AnswerContext, build_context
from app.services.answering.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from app.services.ingestion.documents import get_paper_titles
from app.services.llm import LanguageModel, ModelRequest, ModelUsage
from app.services.retrieval.keyword import search_passages

logger = logging.getLogger(__name__)

NOTHING_RETRIEVED = (
    "No passages matching the question were found in the material searched."
)
NOTHING_FITS = "Matching passages were found, but they were too long to include."


@dataclass(frozen=True)
class AnswerLimits:
    top_k: int
    max_query_chars: int
    max_context_chars: int
    max_output_tokens: int
    timeout_seconds: float
    malformed_retries: int

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        return cls(
            top_k=settings.answer_top_k,
            max_query_chars=settings.max_query_chars,
            max_context_chars=settings.max_context_chars,
            max_output_tokens=settings.llm_max_output_tokens,
            timeout_seconds=settings.llm_timeout_seconds,
            malformed_retries=settings.llm_malformed_retries,
        )


@dataclass(frozen=True)
class ModelRun:
    """A schema-valid model answer, with what produced it. Citations unchecked."""

    answer: ModelAnswer
    context: AnswerContext
    model: str | None  # None when no model was called
    prompt_version: str | None
    usage: ModelUsage  # across all attempts
    attempts: int


def _no_evidence(context: AnswerContext) -> ModelRun:
    """The answer when there is nothing to show the model (FR-QA-004)."""
    logger.info("answering skipped_model dropped=%d", context.passages_dropped)
    return ModelRun(
        answer=ModelAnswer(
            statements=(),
            evidence_sufficiency="insufficient",
            limitations=NOTHING_FITS if context.dropped else NOTHING_RETRIEVED,
        ),
        context=context,
        model=None,
        prompt_version=None,
        usage=ModelUsage(0, 0),
        attempts=0,
    )


def request_answer(
    model: LanguageModel, context: AnswerContext, limits: AnswerLimits
) -> ModelRun:
    """Call the model, retrying only malformed output, within the limit."""
    request = ModelRequest(
        system=SYSTEM_PROMPT,
        user=context.user_message,
        output_schema=answer_json_schema(),
        max_output_tokens=limits.max_output_tokens,
        timeout_seconds=limits.timeout_seconds,
    )
    input_tokens = output_tokens = attempts = 0
    while True:
        attempts += 1
        response = model.generate(request)
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens
        try:
            answer = parse_answer(response.text)
        except MalformedAnswerError:
            logger.warning("answering malformed_output attempt=%d", attempts)
            if attempts > limits.malformed_retries:
                raise
            continue
        return ModelRun(
            answer=answer,
            context=context,
            model=response.model,
            prompt_version=PROMPT_VERSION,
            usage=ModelUsage(input_tokens, output_tokens),
            attempts=attempts,
        )


class Answering:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        model: LanguageModel,
        limits: AnswerLimits,
    ) -> None:
        self._sessions = sessions
        self._model = model
        self._limits = limits

    def ask(
        self,
        question: str,
        *,
        document_ids: Collection[uuid.UUID] | None = None,
        paper_ids: Collection[uuid.UUID] | None = None,
    ) -> ModelRun:
        limits = self._limits
        passages = search_passages(
            self._sessions,
            question,
            k=limits.top_k,
            max_query_chars=limits.max_query_chars,
            document_ids=document_ids,
            paper_ids=paper_ids,
        )
        context = build_context(
            question,
            passages,
            paper_titles=get_paper_titles(
                self._sessions, {passage.paper_id for passage in passages}
            ),
            max_chars=limits.max_context_chars,
        )
        if not context.aliases:
            return _no_evidence(context)
        return request_answer(self._model, context, limits)

"""Assess a document against the checklist (R6; FR-REP-001 to FR-REP-004).

For each item: one retrieval and one model call (AD-006), then the rules decide
what may be stored. Everything is saved in one transaction after the last item,
so a failure part-way stores nothing and raises a specific error.

A document that is not parsed, or has no body text, is never sent to the model
and every item is `needs_review`: a poor parse must not read as "not found"
(FR-REP-002). A re-run adds a new assessment and keeps earlier ones (DR-008).

Logs carry counts only, never paper text (NFR-PRI-002).
"""

import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import (
    Document,
    Passage,
    ReproducibilityAssessment,
    ReproducibilityItem,
    ReproducibilityItemPassage,
)
from app.schemas.answer import MalformedAnswerError
from app.schemas.assessment import (
    ModelAssessment,
    assessment_json_schema,
    parse_assessment,
)
from app.services.answering.context import build_context
from app.services.answering.pipeline import AnswerLimits
from app.services.ingestion.documents import DocumentNotFoundError, get_paper_titles
from app.services.llm import LanguageModel, ModelRequest
from app.services.reproducibility.checklist import (
    CHECKLIST,
    CHECKLIST_VERSION,
    ChecklistItem,
)
from app.services.reproducibility.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from app.services.reproducibility.rules import Decision, decide
from app.services.retrieval.keyword import RetrievedPassage
from app.services.retrieval.selection import Retriever

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ItemResult:
    item: ChecklistItem
    decision: Decision
    examined: Sequence[RetrievedPassage]


def assessment_limits(settings: Settings) -> AnswerLimits:
    return replace(
        AnswerLimits.from_settings(settings), top_k=settings.assessment_top_k
    )


def _brief(item: ChecklistItem) -> str:
    return (
        f"{item.title}. {item.question} "
        f"Reported means: {item.reported} "
        f"Partly reported means: {item.partially_reported}"
    )


class Assessor:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        model: LanguageModel,
        limits: AnswerLimits,
        retriever: Retriever,
    ) -> None:
        self._sessions = sessions
        self._model = model
        self._limits = limits
        self._retrieve = retriever
        self._used_model: str | None = None
        self._method: str | None = None

    def assess(self, document_id: uuid.UUID) -> uuid.UUID:
        """Assess every item and store the result. Returns the assessment id."""
        status = self._document_status(document_id)
        self._used_model = self._method = None
        if status == "parsed" and self._has_body(document_id):
            results = [self._assess_item(document_id, item) for item in CHECKLIST]
        else:
            results = [
                _ItemResult(
                    item, Decision("needs_review", "parse_incomplete", None), ()
                )
                for item in CHECKLIST
            ]
        logger.info("assessment items=%d", len(results))
        return self._store(document_id, status, results)

    def _document_status(self, document_id: uuid.UUID) -> str:
        with self._sessions() as session:
            status = session.scalar(
                select(Document.status).where(Document.id == document_id)
            )
        if status is None:
            raise DocumentNotFoundError(str(document_id))
        return status

    def _has_body(self, document_id: uuid.UUID) -> bool:
        with self._sessions() as session:
            return bool(
                session.scalar(
                    select(
                        exists().where(
                            Passage.document_id == document_id,
                            Passage.region == "body",
                        )
                    )
                )
            )

    def _assess_item(self, document_id: uuid.UUID, item: ChecklistItem) -> _ItemResult:
        limits = self._limits
        retrieval = self._retrieve(
            f"{item.title}. {item.question}",
            k=limits.top_k,
            max_query_chars=limits.max_query_chars,
            document_ids=[document_id],
            paper_ids=None,
        )
        context = build_context(
            _brief(item),
            retrieval.passages,
            paper_titles=get_paper_titles(
                self._sessions, {p.paper_id for p in retrieval.passages}
            ),
            max_chars=limits.max_context_chars,
        )
        if not context.aliases:
            return _ItemResult(
                item, Decision("needs_review", "evidence_unverified", None), ()
            )
        self._method = retrieval.method
        output = self._ask(context.user_message)
        return _ItemResult(
            item, decide(output, context.aliases), tuple(context.aliases.values())
        )

    def _ask(self, user_message: str) -> ModelAssessment:
        limits = self._limits
        request = ModelRequest(
            system=SYSTEM_PROMPT,
            user=user_message,
            output_schema=assessment_json_schema(),
            max_output_tokens=limits.max_output_tokens,
            timeout_seconds=limits.timeout_seconds,
        )
        attempts = 0
        while True:
            attempts += 1
            response = self._model.generate(request)
            self._used_model = response.model
            try:
                return parse_assessment(response.text)
            except MalformedAnswerError:
                logger.warning("assessment malformed_output attempt=%d", attempts)
                if attempts > limits.malformed_retries:
                    raise

    def _store(
        self,
        document_id: uuid.UUID,
        status: str,
        results: Sequence[_ItemResult],
    ) -> uuid.UUID:
        with self._sessions.begin() as session:
            assessment = ReproducibilityAssessment(
                document_id=document_id,
                checklist_version=CHECKLIST_VERSION,
                document_status=status,
                model=self._used_model,
                prompt_version=PROMPT_VERSION if self._used_model else None,
                retrieval_method=self._method,
            )
            session.add(assessment)
            session.flush()
            for result in results:
                _add_item(session, assessment.id, result)
            return assessment.id


def _add_item(session: Session, assessment_id: uuid.UUID, result: _ItemResult) -> None:
    decision = result.decision
    item = ReproducibilityItem(
        assessment_id=assessment_id,
        item_key=result.item.key,
        status=decision.status,
        review_reason=decision.review_reason,
        explanation=decision.explanation,
    )
    session.add(item)
    session.flush()
    session.add_all(_links(item.id, result.examined, decision.quotes))


def _links(
    item_id: uuid.UUID,
    examined: Sequence[RetrievedPassage],
    quotes: Mapping[uuid.UUID, str],
) -> list[ReproducibilityItemPassage]:
    return [
        ReproducibilityItemPassage(
            item_id=item_id,
            passage_id=passage.passage_id,
            quote=quotes.get(passage.passage_id),
        )
        for passage in examined
    ]

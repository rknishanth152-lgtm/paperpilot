"""The final answer returned to clients (P5-T9; PRD §9.1).

Pages, sections and passage text come from the database, never from the model
(AD-007, FR-CIT-003). `claim_support` can only be `not_evaluated`: nothing here
establishes that a passage supports a statement (FR-CIT-005, AD-008).
"""

import uuid
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator


class _Response(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QuestionRequest(_Response):
    """A question about selected papers (FR-QA-001): at least one id is required."""

    question: str
    document_ids: tuple[uuid.UUID, ...] | None = None
    paper_ids: tuple[uuid.UUID, ...] | None = None

    @model_validator(mode="after")
    def scope_given(self) -> Self:
        if not self.document_ids and not self.paper_ids:
            raise ValueError("a scope is required")
        return self


class CitationResponse(_Response):
    """`passage_id` is set only for a valid citation; `reason` only for an invalid one."""

    alias: str
    quote: str | None
    valid: bool
    reason: (
        Literal["passage_not_found", "not_in_context", "wrong_paper", "quote_mismatch"]
        | None
    )
    passage_id: uuid.UUID | None


class StatementResponse(_Response):
    text: str
    citations: tuple[CitationResponse, ...]
    has_valid_citation: bool


class EvidencePassage(_Response):
    """A stored passage cited by a valid citation. A null page means unknown."""

    alias: str
    passage_id: uuid.UUID
    document_id: uuid.UUID
    paper_id: uuid.UUID
    paper_title: str | None
    section: str | None
    page_start: int | None
    page_end: int | None
    text: str


class AnswerResponse(_Response):
    statements: tuple[StatementResponse, ...]
    evidence: tuple[EvidencePassage, ...]
    evidence_sufficiency: Literal["sufficient", "partial", "insufficient"]
    limitations: str | None
    validation_status: Literal["validated", "failed"]
    claim_support: Literal["not_evaluated"]
    retrieved_passage_ids: tuple[uuid.UUID, ...]
    passages_dropped: int
    retrieval_method: str
    model: str | None  # null when no model was called
    prompt_version: str | None

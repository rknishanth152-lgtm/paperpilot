"""The checklist as returned to clients (R7; FR-REP-002, FR-REP-004).

There is deliberately no score, total or verdict. A null section or page means
unknown. Locations and passage text come from the database (AD-007).
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Response(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)


class AssessmentEvidence(_Response):
    passage_id: uuid.UUID
    section: str | None
    page_start: int | None
    page_end: int | None
    quote: str
    text: str


class AssessmentItem(_Response):
    key: str
    title: str
    question: str
    status: Literal["reported", "partially_reported", "not_found", "needs_review"]
    status_label: str
    status_description: str
    review_reason: (
        Literal["parse_incomplete", "evidence_unverified", "model_uncertain"] | None
    )
    explanation: str | None
    passages_examined: int
    evidence: tuple[AssessmentEvidence, ...]


class AssessmentResponse(_Response):
    assessment_id: uuid.UUID
    document_id: uuid.UUID
    checklist_version: str
    document_status: Literal["pending", "processing", "parsed", "failed"]
    model: str | None  # null when no model was called
    prompt_version: str | None
    retrieval_method: str | None
    created_at: datetime
    items: tuple[AssessmentItem, ...]

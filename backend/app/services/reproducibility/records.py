"""Reading assessments for the API (R7; FR-REP-002, FR-REP-004, DR-001).

Plain records, so routes never query tables (NFR-MNT-001). Locations and passage
text come from the stored passage, never from the model (AD-007).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Passage,
    ReproducibilityAssessment,
    ReproducibilityItem,
    ReproducibilityItemPassage,
)
from app.services.ingestion.documents import get_document
from app.services.reproducibility.checklist import CHECKLIST, ChecklistItem
from app.services.reproducibility.wording import status_text


class AssessmentNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class EvidenceRecord:
    passage_id: uuid.UUID
    section: str | None
    page_start: int | None
    page_end: int | None
    quote: str
    text: str


@dataclass(frozen=True)
class ItemRecord:
    key: str
    title: str
    question: str
    status: str
    status_label: str
    status_description: str
    review_reason: str | None
    explanation: str | None
    passages_examined: int
    evidence: list[EvidenceRecord]


@dataclass(frozen=True)
class AssessmentRecord:
    assessment_id: uuid.UUID
    document_id: uuid.UUID
    checklist_version: str
    document_status: str
    model: str | None
    prompt_version: str | None
    retrieval_method: str | None
    created_at: datetime
    items: list[ItemRecord]


def get_latest_assessment(
    sessions: sessionmaker[Session], document_id: uuid.UUID
) -> AssessmentRecord:
    """The newest assessment. Raises DocumentNotFoundError or AssessmentNotFoundError."""
    get_document(sessions, document_id)
    with sessions() as session:
        assessment_id = session.scalar(
            select(ReproducibilityAssessment.id)
            .where(ReproducibilityAssessment.document_id == document_id)
            .order_by(
                ReproducibilityAssessment.created_at.desc(),
                ReproducibilityAssessment.id.desc(),
            )
            .limit(1)
        )
    if assessment_id is None:
        raise AssessmentNotFoundError(str(document_id))
    return get_assessment(sessions, assessment_id)


def get_assessment(
    sessions: sessionmaker[Session], assessment_id: uuid.UUID
) -> AssessmentRecord:
    with sessions() as session:
        assessment = session.get_one(ReproducibilityAssessment, assessment_id)
        stored = {
            item.item_key: item
            for item in session.scalars(
                select(ReproducibilityItem).where(
                    ReproducibilityItem.assessment_id == assessment_id
                )
            )
        }
        return AssessmentRecord(
            assessment_id=assessment.id,
            document_id=assessment.document_id,
            checklist_version=assessment.checklist_version,
            document_status=assessment.document_status,
            model=assessment.model,
            prompt_version=assessment.prompt_version,
            retrieval_method=assessment.retrieval_method,
            created_at=assessment.created_at,
            items=[
                _item_record(session, definition, stored[definition.key])
                for definition in CHECKLIST
            ],
        )


def _item_record(
    session: Session, definition: ChecklistItem, item: ReproducibilityItem
) -> ItemRecord:
    rows = session.execute(
        select(
            ReproducibilityItemPassage.quote,
            Passage.id,
            Passage.section_path,
            Passage.page_start,
            Passage.page_end,
            Passage.text,
        )
        .join(Passage, ReproducibilityItemPassage.passage_id == Passage.id)
        .where(ReproducibilityItemPassage.item_id == item.id)
        .order_by(Passage.ordinal)
    ).all()
    label, description = status_text(item.status, item.review_reason)
    return ItemRecord(
        key=definition.key,
        title=definition.title,
        question=definition.question,
        status=item.status,
        status_label=label,
        status_description=description,
        review_reason=item.review_reason,
        explanation=item.explanation,
        passages_examined=len(rows),
        evidence=[
            EvidenceRecord(
                passage_id=row.id,
                section=row.section_path,
                page_start=row.page_start,
                page_end=row.page_end,
                quote=row.quote,
                text=row.text,
            )
            for row in rows
            if row.quote is not None
        ],
    )

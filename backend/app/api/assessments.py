"""The reproducibility checklist routes (R7; FR-REP-002, FR-REP-004).

Reading runs nothing. Running calls the model once per checklist item and is
blocking, so it is a plain function that runs in FastAPI's thread pool.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_assessor, get_sessions
from app.schemas.assessment_response import AssessmentResponse
from app.schemas.documents import ErrorResponse
from app.services.reproducibility.assessment import Assessor
from app.services.reproducibility.records import get_assessment, get_latest_assessment

router = APIRouter(prefix="/documents", tags=["assessments"])

Sessions = Annotated[sessionmaker[Session], Depends(get_sessions)]
ERRORS: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse} for status in (404, 422, 429, 502, 503, 504)
}


@router.get("/{document_id}/assessment", responses=ERRORS)
def read_assessment(document_id: uuid.UUID, sessions: Sessions) -> AssessmentResponse:
    return AssessmentResponse.model_validate(
        get_latest_assessment(sessions, document_id)
    )


@router.post("/{document_id}/assessment", responses=ERRORS)
def run_assessment(
    document_id: uuid.UUID,
    sessions: Sessions,
    assessor: Annotated[Assessor, Depends(get_assessor)],
) -> AssessmentResponse:
    """Assess the document and return the new assessment. Earlier ones are kept."""
    return AssessmentResponse.model_validate(
        get_assessment(sessions, assessor.assess(document_id))
    )

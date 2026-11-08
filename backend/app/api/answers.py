"""The answers route (P5-T11; FR-QA-001, FR-UI-003).

A failed citation check is a normal 200 response marked `validation_status:
failed`. Errors are for when no answer exists at all. Blocking work, so this is
a plain function that runs in FastAPI's thread pool.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_answering
from app.schemas.answer_response import AnswerResponse, QuestionRequest
from app.schemas.documents import ErrorResponse
from app.services.answering.pipeline import Answering

router = APIRouter(prefix="/answers", tags=["answers"])

ERRORS: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse} for status in (422, 429, 502, 503, 504)
}


@router.post("", responses=ERRORS)
def create_answer(
    body: QuestionRequest, answering: Annotated[Answering, Depends(get_answering)]
) -> AnswerResponse:
    return answering.answer(
        body.question, document_ids=body.document_ids, paper_ids=body.paper_ids
    )

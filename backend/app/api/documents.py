"""Document routes: upload, status, structure, retry (P3-T8).

Upload body: the PDF bytes themselves (any `Content-Type`; the type is decided
by content). Optional `X-Filename` header: the client's file name,
percent-encoded UTF-8, used for display only (NFR-SEC-002). The body is read
in chunks and reading stops once it passes `MAX_UPLOAD_MB` (decided P3-T8:
raw body instead of multipart, no extra dependency).

Processing runs after the response in the same process; clients poll the
status (AD-010).
"""

import uuid
from typing import Annotated, Any
from urllib.parse import unquote

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, Response
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_ingestion, get_sessions
from app.config import Settings, get_settings
from app.schemas.documents import (
    DocumentResponse,
    ErrorResponse,
    StructureResponse,
    UploadResponse,
)
from app.services.ingestion import documents
from app.services.ingestion.pipeline import Ingestion
from app.services.ingestion.validation import UploadRejectedError, validate_upload

router = APIRouter(prefix="/documents", tags=["documents"])

Sessions = Annotated[sessionmaker[Session], Depends(get_sessions)]
IngestionDep = Annotated[Ingestion, Depends(get_ingestion)]
ERRORS: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse} for status in (404, 409, 422, 500)
}


async def read_limited(request: Request, max_bytes: int) -> bytes:
    """The request body, or `file_too_large` as soon as it exceeds `max_bytes`."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > max_bytes:
        raise UploadRejectedError("file_too_large")
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > max_bytes:
            raise UploadRejectedError("file_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "",
    status_code=202,
    responses={
        200: {"model": UploadResponse},
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        **ERRORS,
    },
)
async def upload_document(
    request: Request,
    response: Response,
    background: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings)],
    ingestion: IngestionDep,
    sessions: Sessions,
    x_filename: Annotated[str | None, Header()] = None,
) -> UploadResponse:
    """202 and `created: true` for a new file; 200 and the existing document
    for an identical one (which is not processed again)."""
    data = await read_limited(request, settings.max_upload_bytes)
    filename = unquote(x_filename, errors="replace") if x_filename is not None else None
    upload = validate_upload(data, filename, max_bytes=settings.max_upload_bytes)
    registration = await run_in_threadpool(ingestion.register, upload)
    if registration.created:
        background.add_task(
            documents.process_in_background, ingestion, registration.document_id
        )
    else:
        response.status_code = 200
    record = await run_in_threadpool(
        documents.get_document, sessions, registration.document_id
    )
    return UploadResponse.model_validate(
        {
            **DocumentResponse.model_validate(record).model_dump(),
            "created": registration.created,
        }
    )


@router.get("/{document_id}", responses=ERRORS)
def get_document(document_id: uuid.UUID, sessions: Sessions) -> DocumentResponse:
    return DocumentResponse.model_validate(
        documents.get_document(sessions, document_id)
    )


@router.get("/{document_id}/structure", responses=ERRORS)
def get_structure(document_id: uuid.UUID, sessions: Sessions) -> StructureResponse:
    """Metadata and passages in order; 409 with status and reason if not parsed."""
    record = documents.get_structure(sessions, document_id)
    return StructureResponse.model_validate(
        {
            "document_id": record.document_id,
            "status": "parsed",
            "parser": {"name": record.parser_name, "version": record.parser_version},
            "page_count": record.page_count,
            "paper": record.paper,
            "passages": record.passages,
        }
    )


@router.post("/{document_id}/retry", status_code=202, responses=ERRORS)
def retry_document(
    document_id: uuid.UUID,
    background: BackgroundTasks,
    sessions: Sessions,
    ingestion: IngestionDep,
) -> DocumentResponse:
    """Process a `failed` (or stuck `pending`) document again; poll its status."""
    record = documents.check_retryable(sessions, document_id)
    background.add_task(documents.process_in_background, ingestion, document_id)
    return DocumentResponse.model_validate(record)

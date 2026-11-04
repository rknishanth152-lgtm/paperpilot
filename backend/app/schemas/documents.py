"""External contracts of the document API (P3-T8)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

DocumentStatus = Literal["pending", "processing", "parsed", "failed"]


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class DocumentResponse(_Contract):
    """A document's processing status. `failure_explanation` is plain language."""

    document_id: uuid.UUID
    status: DocumentStatus
    failure_reason: str | None
    failure_explanation: str | None
    original_filename: str | None
    sha256: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class UploadResponse(DocumentResponse):
    """`created` is false when an identical file was already uploaded (PRD §8.3)."""

    created: bool


class ParserInfo(_Contract):
    name: str
    version: str


class PaperResponse(_Contract):
    paper_id: uuid.UUID
    title: str | None
    authors: list[str]
    abstract: str | None
    doi: str | None


class PassageResponse(_Contract):
    """Stored source text, exactly as stored. A null page means unknown (DR-007)."""

    passage_id: uuid.UUID
    ordinal: int
    region: Literal["abstract", "body", "caption", "back"]
    back_type: str | None
    section_number: str | None
    section_title: str | None
    text: str
    page_start: int | None
    page_end: int | None


class StructureResponse(_Contract):
    document_id: uuid.UUID
    status: Literal["parsed"]
    parser: ParserInfo
    page_count: int | None
    paper: PaperResponse
    passages: list[PassageResponse]


class ErrorBody(_Contract):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(_Contract):
    """Every API error has this shape, with no internals (NFR-SEC-005)."""

    error: ErrorBody

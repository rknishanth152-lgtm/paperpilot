"""Reading documents for the API (P3-T8; FR-ING-009).

Returns plain records, so routes never query tables (NFR-MNT-001). The stored
`failure_message` is deliberately left out: it is for developers, and users
see the explanation for the reason code instead.
"""

import logging
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Document, Paper, Passage
from app.services.ingestion.explanations import FAILURE_EXPLANATIONS
from app.services.ingestion.pipeline import PROCESSABLE, DocumentStateError, Ingestion

logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    pass


class DocumentNotParsedError(Exception):
    def __init__(self, status: str, failure_reason: str | None) -> None:
        super().__init__(status)
        self.status = status
        self.failure_reason = failure_reason


class DocumentNotRetryableError(Exception):
    def __init__(self, status: str) -> None:
        super().__init__(status)
        self.status = status


@dataclass(frozen=True)
class DocumentRecord:
    document_id: uuid.UUID
    status: str
    failure_reason: str | None
    failure_explanation: str | None
    original_filename: str | None
    sha256: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PaperRecord:
    paper_id: uuid.UUID
    title: str | None
    authors: list[str]
    abstract: str | None
    doi: str | None


@dataclass(frozen=True)
class PassageRecord:
    passage_id: uuid.UUID
    ordinal: int
    region: str
    back_type: str | None
    section_number: str | None
    section_title: str | None
    text: str
    page_start: int | None
    page_end: int | None


@dataclass(frozen=True)
class StructureRecord:
    document_id: uuid.UUID
    parser_name: str
    parser_version: str
    page_count: int | None
    paper: PaperRecord
    passages: list[PassageRecord]


def get_document(
    sessions: sessionmaker[Session], document_id: uuid.UUID
) -> DocumentRecord:
    with sessions() as session:
        return _record(_load(session, document_id))


def get_structure(
    sessions: sessionmaker[Session], document_id: uuid.UUID
) -> StructureRecord:
    """Metadata and passages in order. Only `parsed` documents have a structure."""
    with sessions() as session:
        document = _load(session, document_id)
        if document.status != "parsed":
            raise DocumentNotParsedError(document.status, document.failure_reason)
        # The schema guarantees these for parsed documents (ck_documents_parsed_*).
        assert document.paper_id is not None
        assert document.parser_name is not None and document.parser_version is not None
        paper = session.get_one(Paper, document.paper_id)
        passages = session.scalars(
            select(Passage)
            .where(Passage.document_id == document_id)
            .order_by(Passage.ordinal)
        )
        return StructureRecord(
            document_id=document.id,
            parser_name=document.parser_name,
            parser_version=document.parser_version,
            page_count=document.page_count,
            paper=PaperRecord(
                paper_id=paper.id,
                title=paper.title,
                authors=list(paper.authors),
                abstract=paper.abstract,
                doi=paper.doi,
            ),
            passages=[
                PassageRecord(
                    passage_id=passage.id,
                    ordinal=passage.ordinal,
                    region=passage.region,
                    back_type=passage.back_type,
                    section_number=passage.section_number,
                    section_title=passage.section_title,
                    text=passage.text,
                    page_start=passage.page_start,
                    page_end=passage.page_end,
                )
                for passage in passages
            ],
        )


def check_retryable(
    sessions: sessionmaker[Session], document_id: uuid.UUID
) -> DocumentRecord:
    """A `failed` document may be retried. So may a `pending` one, which a
    stopped server can leave behind before processing began."""
    document = get_document(sessions, document_id)
    if document.status not in PROCESSABLE:
        raise DocumentNotRetryableError(document.status)
    return document


def process_in_background(ingestion: Ingestion, document_id: uuid.UUID) -> None:
    """Run processing after the response is sent (AD-010: status polling).

    Another request may have started this document in the meantime; the row
    lock in `Ingestion.process` lets only one run, and the other stops here.

    A database error stops here too, or the server would log its text, and
    PostgreSQL's message can quote the row being written (NFR-PRI-002). Nothing
    was committed: the document stays as it was until startup recovery marks it
    `interrupted` (FR-ING-010).
    """
    try:
        ingestion.process(document_id)
    except DocumentStateError as error:
        logger.info("ingestion document_id=%s skipped: %s", document_id, error)
    except SQLAlchemyError as error:
        logger.error(
            "ingestion document_id=%s database failure: %s",
            document_id,
            type(error).__name__,
        )


def get_paper_titles(
    sessions: sessionmaker[Session], paper_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, str | None]:
    """Stored titles by paper id. A paper with no parsed title maps to None."""
    with sessions() as session:
        rows = session.execute(
            select(Paper.id, Paper.title).where(Paper.id.in_(paper_ids))
        )
        return {row.id: row.title for row in rows}


def _load(session: Session, document_id: uuid.UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise DocumentNotFoundError(str(document_id))
    return document


def _record(document: Document) -> DocumentRecord:
    reason = document.failure_reason
    return DocumentRecord(
        document_id=document.id,
        status=document.status,
        failure_reason=reason,
        failure_explanation=FAILURE_EXPLANATIONS[reason] if reason else None,
        original_filename=document.original_filename,
        sha256=document.sha256,
        size_bytes=document.size_bytes,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )

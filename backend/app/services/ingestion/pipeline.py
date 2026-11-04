"""Ingestion orchestration (P3-T5, P3-T6; FR-ING-002, FR-ING-003, FR-ING-005..008).

register: an identical file (same SHA-256) returns the existing document and
stores nothing. Otherwise store the PDF, then create a `pending` document; if
the row cannot be created, the stored file is removed again. When identical
uploads race, the unique hash decides: the loser removes its copy and gets the
winner's document (NFR-REL-002).

process: `pending` or `failed` (retry) -> `processing` -> GROBID -> store raw TEI ->
one transaction that writes the paper, all passages and `parsed`. Every
expected failure ends in `failed` with one failure_reason and no passages.
The GROBID call runs outside any database transaction because it can take
seconds. If the database itself fails in the final step, nothing is written
and the document stays `processing`; startup recovery marks it `interrupted`
(FR-ING-010, P3-T7). A row lock plus the status check lets only one `process`
call run per document, so passages are never written twice. TEI files from
failed attempts stay in storage; nothing is deleted automatically (DR-008).

Logs carry ids, statuses and reasons only, never paper text (NFR-PRI-002).
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Document, Paper, Passage
from app.services.doi import normalize_doi
from app.services.ingestion.grobid import ParserFailure
from app.services.ingestion.tei import ParsedDocument, ParseError, parse_tei
from app.services.ingestion.validation import ValidatedUpload
from app.storage import Storage, StorageError

logger = logging.getLogger(__name__)

MAX_FAILURE_MESSAGE = 1000  # documents.failure_message CHECK
PROCESSABLE = ("pending", "failed")  # failed documents may be retried (FR-ING-008)
_UNIQUE_HASH = "uq_documents_sha256"


@dataclass(frozen=True)
class Registration:
    document_id: uuid.UUID
    created: bool  # False: an identical file was already registered


class Parser(Protocol):
    @property
    def parser_config(self) -> dict[str, Any]: ...

    def process_fulltext(self, pdf: bytes) -> bytes: ...


class DocumentStateError(Exception):
    """The document does not exist or is not in a state that allows the action."""


class Ingestion:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        storage: Storage,
        parser: Parser,
        *,
        parse: Callable[[bytes], ParsedDocument] = parse_tei,
    ) -> None:
        self._sessions = sessions
        self._storage = storage
        self._parser = parser
        self._parse = parse

    def register(self, upload: ValidatedUpload) -> Registration:
        """Return the document for this file, creating it if it is new."""
        existing = self._find_by_hash(upload.sha256)
        if existing is not None:
            return Registration(existing, created=False)

        key = self._storage.save(upload.content, kind="pdf")
        try:
            with self._sessions.begin() as session:
                document = Document(
                    sha256=upload.sha256,
                    size_bytes=upload.size_bytes,
                    storage_key=key,
                    original_filename=upload.original_filename,
                )
                session.add(document)
                session.flush()
                document_id = document.id
        except IntegrityError as error:
            self._remove_unclaimed(key)
            if _violated(error) == _UNIQUE_HASH:
                # An identical upload won the race; return its document.
                winner = self._find_by_hash(upload.sha256)
                if winner is not None:
                    return Registration(winner, created=False)
            raise
        except BaseException:
            self._remove_unclaimed(key)
            raise
        logger.info("ingestion document_id=%s status=pending", document_id)
        return Registration(document_id, created=True)

    def process(self, document_id: uuid.UUID) -> str:
        """Parse a `pending` or `failed` document; return its final status."""
        storage_key = self._start(document_id)

        try:
            pdf = self._storage.read(storage_key)
        except StorageError as exc:
            return self._fail(document_id, "storage_error", str(exc))

        try:
            tei = self._parser.process_fulltext(pdf)
        except ParserFailure as failure:
            return self._fail(document_id, failure.reason, failure.message)
        if not tei:
            return self._fail(document_id, "empty_parse", "parser returned no content")

        try:
            tei_key = self._storage.save(tei, kind="tei")
        except StorageError as exc:
            return self._fail(document_id, "storage_error", str(exc))

        try:
            parsed = self._parse(tei)
        except ParseError as error:
            return self._fail(document_id, error.reason, error.message, tei_key=tei_key)

        self._persist(document_id, parsed, tei_key)
        logger.info(
            "ingestion document_id=%s status=parsed passages=%d skipped=%d joined=%d",
            document_id,
            len(parsed.passages),
            parsed.skipped_paragraphs,
            parsed.joined_paragraphs,
        )
        return "parsed"

    def _start(self, document_id: uuid.UUID) -> str:
        with self._sessions.begin() as session:
            document = session.get(Document, document_id, with_for_update=True)
            if document is None:
                raise DocumentStateError("document not found")
            if document.status not in PROCESSABLE:
                raise DocumentStateError(
                    f"document is {document.status}; cannot process"
                )
            retry = document.status == "failed"
            document.status = "processing"
            document.failure_reason = None
            document.failure_message = None
            document.processing_started_at = func.now()
            storage_key = document.storage_key
        logger.info(
            "ingestion document_id=%s status=processing retry=%s", document_id, retry
        )
        return storage_key

    def _find_by_hash(self, sha256: str) -> uuid.UUID | None:
        with self._sessions() as session:
            return session.scalar(select(Document.id).where(Document.sha256 == sha256))

    def _remove_unclaimed(self, key: str) -> None:
        """No row claims this file, so it must not stay behind (FR-ING-002)."""
        try:
            self._storage.delete(key)
        except StorageError:
            logger.error("ingestion cleanup failed storage_key=%s", key)

    def _persist(
        self, document_id: uuid.UUID, parsed: ParsedDocument, tei_key: str
    ) -> None:
        """Paper, passages and `parsed` in one transaction (all or nothing)."""
        with self._sessions.begin() as session:
            document = session.get(Document, document_id, with_for_update=True)
            if document is None:
                raise DocumentStateError("document not found")
            paper = self._paper_for(session, parsed)
            session.add_all(
                Passage(
                    document_id=document_id,
                    ordinal=passage.ordinal,
                    region=passage.region,
                    back_type=passage.back_type,
                    section_number=passage.section_number,
                    section_title=passage.section_title,
                    text=passage.text,
                    page_start=passage.page_start,
                    page_end=passage.page_end,
                )
                for passage in parsed.passages
            )
            document.paper_id = paper.id
            document.status = "parsed"
            document.parser_name = parsed.parser_name
            document.parser_version = parsed.parser_version
            document.parser_config = self._parser.parser_config
            document.tei_storage_key = tei_key
            document.page_count = parsed.page_count
            document.skipped_paragraphs = parsed.skipped_paragraphs
            document.joined_paragraphs = parsed.joined_paragraphs

    @staticmethod
    def _paper_for(session: Session, parsed: ParsedDocument) -> Paper:
        """The paper with the same DOI, else a new paper from this parse.

        An existing paper's metadata is never overwritten (DR-008, PRD §8.3).
        """
        doi_normalized = normalize_doi(parsed.doi)
        if doi_normalized is not None:
            existing = session.scalar(
                select(Paper).where(Paper.doi_normalized == doi_normalized)
            )
            if existing is not None:
                return existing
        paper = Paper(
            title=parsed.title,
            authors=parsed.authors,
            abstract=parsed.abstract,
            doi=parsed.doi.strip()
            if doi_normalized is not None and parsed.doi
            else None,
            doi_normalized=doi_normalized,
            metadata_source="grobid",
        )
        session.add(paper)
        session.flush()
        return paper

    def _fail(
        self,
        document_id: uuid.UUID,
        reason: str,
        message: str,
        *,
        tei_key: str | None = None,
    ) -> str:
        with self._sessions.begin() as session:
            document = session.get(Document, document_id, with_for_update=True)
            if document is None:
                raise DocumentStateError("document not found")
            document.status = "failed"
            document.failure_reason = reason
            document.failure_message = message[:MAX_FAILURE_MESSAGE] or None
            document.tei_storage_key = tei_key
            document.parser_config = self._parser.parser_config
        logger.info(
            "ingestion document_id=%s status=failed reason=%s", document_id, reason
        )
        return "failed"


def _violated(error: IntegrityError) -> str | None:
    """Name of the constraint PostgreSQL reported, if any."""
    diag = getattr(error.orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name if isinstance(name, str) else None

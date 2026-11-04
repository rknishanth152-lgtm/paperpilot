"""Ingestion orchestration (P3-T5, FR-ING-002, FR-ING-003, FR-ING-005..007).

register: store the validated PDF, then create a `pending` document. If the row
cannot be created, the stored file is removed again.

process: `pending` -> `processing` -> GROBID -> store raw TEI -> parse ->
one transaction that writes the paper, all passages and `parsed`. Every
expected failure ends in `failed` with one failure_reason and no passages.
The GROBID call runs outside any database transaction because it can take
seconds. If the database itself fails in the final step, nothing is written
and the document stays `processing`; startup recovery marks it `interrupted`
(FR-ING-010, P3-T7).

Duplicate uploads and retries of failed documents are P3-T6.
Logs carry ids, statuses and reasons only, never paper text (NFR-PRI-002).
"""

import logging
import uuid
from collections.abc import Callable
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Document, Paper, Passage
from app.services.doi import normalize_doi
from app.services.ingestion.grobid import ParserFailure
from app.services.ingestion.tei import ParsedDocument, ParseError, parse_tei
from app.services.ingestion.validation import ValidatedUpload
from app.storage import Storage, StorageError

logger = logging.getLogger(__name__)

MAX_FAILURE_MESSAGE = 1000  # documents.failure_message CHECK


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

    def register(self, upload: ValidatedUpload) -> uuid.UUID:
        """Store the file and create a `pending` document; return its id."""
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
        except BaseException:
            # No row claims this file, so it must not stay behind (FR-ING-002).
            try:
                self._storage.delete(key)
            except StorageError:
                logger.error("ingestion cleanup failed storage_key=%s", key)
            raise
        logger.info("ingestion document_id=%s status=pending", document_id)
        return document_id

    def process(self, document_id: uuid.UUID) -> str:
        """Parse a `pending` document; return its final status."""
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
            if document.status != "pending":
                raise DocumentStateError(f"document is {document.status}, not pending")
            document.status = "processing"
            document.processing_started_at = func.now()
            storage_key = document.storage_key
        logger.info("ingestion document_id=%s status=processing", document_id)
        return storage_key

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

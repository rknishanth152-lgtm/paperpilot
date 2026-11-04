"""Ingestion orchestration against PostgreSQL (P3-T5).

A fake parser stands in for GROBID so every outcome can be forced; storage is
a temporary folder; the database is the throwaway test database.
FR-ING-002, FR-ING-003, FR-ING-005, FR-ING-006, FR-ING-007, PRD §8.3.
"""

import hashlib
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.synthetic import BODY, p, section, tei

from app.models import Document, Paper, Passage
from app.services.ingestion.grobid import ParserFailure
from app.services.ingestion.pipeline import (
    DocumentStateError,
    Ingestion,
)
from app.services.ingestion.tei import ParsedDocument, ParsedPassage
from app.services.ingestion.validation import ValidatedUpload, validate_upload
from app.storage import LocalStorage, StorageError

PDF = b"%PDF-1.4 synthetic test document"


class FakeParser:
    """Returns fixed TEI or raises a fixed ParserFailure."""

    def __init__(
        self, tei_bytes: bytes = b"", failure: ParserFailure | None = None
    ) -> None:
        self.tei_bytes = tei_bytes
        self.failure = failure
        self.received: list[bytes] = []

    @property
    def parser_config(self) -> dict[str, Any]:
        return {"endpoint": "/fake", "form_fields": {"consolidateHeader": "0"}}

    def process_fulltext(self, pdf: bytes) -> bytes:
        self.received.append(pdf)
        if self.failure is not None:
            raise self.failure
        return self.tei_bytes


class TeiStorageFails(LocalStorage):
    def save(self, data: bytes, *, kind: str) -> str:
        if kind == "tei":
            raise StorageError("file could not be stored (OSError)")
        return super().save(data, kind=kind)


class CountingStorage(LocalStorage):
    """Counts PDF saves; optionally holds every saver at a barrier.

    The barrier sits between the hash lookup and the insert in `register`, so
    all concurrent uploads have looked up and found nothing before any of them
    inserts: the race is forced instead of left to timing.
    """

    def __init__(self, root: Path, barrier: threading.Barrier | None = None) -> None:
        super().__init__(root)
        self.pdf_saves = 0
        self._barrier = barrier
        self._lock = threading.Lock()

    def save(self, data: bytes, *, kind: str) -> str:
        if kind == "pdf":
            with self._lock:
                self.pdf_saves += 1
            if self._barrier is not None:
                self._barrier.wait()
        return super().save(data, kind=kind)


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "storage")


def ingestion(
    sessions: sessionmaker[Session],
    storage: LocalStorage,
    parser: FakeParser,
    parse: Callable[[bytes], ParsedDocument] | None = None,
) -> Ingestion:
    kwargs: dict[str, Any] = {} if parse is None else {"parse": parse}
    return Ingestion(sessions, storage, parser, **kwargs)


def upload(content: bytes = PDF, name: str = "paper.pdf") -> Any:
    return validate_upload(content, name, max_bytes=10_000_000)


def get_document(sessions: sessionmaker[Session], document_id: uuid.UUID) -> Document:
    with sessions() as session:
        document = session.get(Document, document_id)
        assert document is not None
        return document


def count(sessions: sessionmaker[Session], model: Any) -> int:
    with sessions() as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def passages_of(
    sessions: sessionmaker[Session], document_id: uuid.UUID
) -> list[Passage]:
    with sessions() as session:
        return list(
            session.scalars(
                select(Passage)
                .where(Passage.document_id == document_id)
                .order_by(Passage.ordinal)
            )
        )


GOOD_TEI = tei(
    header='<idno type="DOI">https://doi.org/10.1234/ABC</idno>',
    abstract=f"<div>{p('A summary.')}</div>",
    body=section(
        "Methods", p("Step one.", "1,1,1,1,1"), p("Step two.", "2,1,1,1,1"), n="2"
    )
    + '<figure coords="2,1,1,1,1"><head>Figure 1 .</head><figDesc>A chart.</figDesc></figure>',
    back='<div type="availability"><div><head>Data availability</head>'
    + p("All data are included.", "2,1,1,1,1")
    + "</div></div>",
)


# --- register -----------------------------------------------------------------------


def test_register_stores_the_file_and_creates_a_pending_document(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    document_id = (
        ingestion(sessions, storage, FakeParser())
        .register(upload(name="My Paper.pdf"))
        .document_id
    )

    document = get_document(sessions, document_id)
    assert document.status == "pending"
    assert document.paper_id is None
    assert document.original_filename == "My Paper.pdf"
    assert document.size_bytes == len(PDF)
    stored = storage.read(document.storage_key)
    assert hashlib.sha256(stored).hexdigest() == document.sha256  # FR-ING-002


def test_failed_register_leaves_no_stored_file(
    sessions: sessionmaker[Session], storage: LocalStorage, tmp_path: Path
) -> None:
    """If the document row cannot be created, the stored file is removed."""
    invalid = ValidatedUpload(
        content=PDF,
        sha256=hashlib.sha256(PDF).hexdigest(),
        size_bytes=0,
        original_filename=None,
    )  # size 0 violates ck_documents_size_positive

    with pytest.raises(IntegrityError):
        ingestion(sessions, storage, FakeParser()).register(invalid)

    assert list((tmp_path / "storage").rglob("*.pdf")) == []
    assert count(sessions, Document) == 0


# --- process: success ------------------------------------------------------------------


def test_process_parses_and_stores_paper_passages_and_provenance(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    parser = FakeParser(GOOD_TEI)
    pipeline = ingestion(sessions, storage, parser)
    document_id = pipeline.register(upload()).document_id

    assert pipeline.process(document_id) == "parsed"

    document = get_document(sessions, document_id)
    assert parser.received == [PDF]
    assert document.status == "parsed"
    assert document.failure_reason is None
    assert (document.parser_name, document.parser_version) == ("grobid", "0.9.1")
    assert document.parser_config == parser.parser_config
    assert document.page_count == 2
    assert (document.skipped_paragraphs, document.joined_paragraphs) == (0, 0)
    assert document.tei_storage_key is not None
    assert storage.read(document.tei_storage_key) == GOOD_TEI  # FR-ING-005

    with sessions() as session:
        paper = session.get(Paper, document.paper_id)
        assert paper is not None
        assert paper.title == "A Synthetic Paper"
        assert paper.authors == ["Ada B Example", "Ben Sample"]
        assert paper.abstract == "A summary."
        assert (paper.doi, paper.doi_normalized) == (
            "https://doi.org/10.1234/ABC",
            "10.1234/abc",
        )
        assert paper.metadata_source == "grobid"

    stored = passages_of(sessions, document_id)
    assert [(x.ordinal, x.region) for x in stored] == [
        (0, "abstract"),
        (1, "body"),
        (2, "body"),
        (3, "caption"),
        (4, "back"),
    ]
    assert stored[1].section_path == "2 Methods"
    assert (stored[2].page_start, stored[2].page_end) == (2, 2)
    assert stored[3].section_title == "Figure 1"
    assert stored[4].back_type == "availability"


def test_same_doi_attaches_to_the_existing_paper_without_overwriting(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    first = ingestion(sessions, storage, FakeParser(GOOD_TEI))
    first_id = first.register(upload(PDF + b" v1")).document_id
    first.process(first_id)

    renamed = GOOD_TEI.replace(b"A Synthetic Paper", b"A Different Title")
    second = ingestion(sessions, storage, FakeParser(renamed))
    second_id = second.register(upload(PDF + b" v2")).document_id
    second.process(second_id)

    assert (
        get_document(sessions, first_id).paper_id
        == get_document(sessions, second_id).paper_id
    )
    assert count(sessions, Paper) == 1
    with sessions() as session:
        assert session.scalar(select(Paper.title)) == "A Synthetic Paper"


def test_documents_without_doi_get_separate_papers(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    no_doi = tei(body=BODY)
    for content in (PDF + b" a", PDF + b" b"):
        pipeline = ingestion(sessions, storage, FakeParser(no_doi))
        pipeline.process(pipeline.register(upload(content)).document_id)

    assert count(sessions, Paper) == 2
    with sessions() as session:
        assert session.scalars(select(Paper.doi)).all() == [None, None]


def test_value_that_is_not_a_doi_is_stored_as_no_doi(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    pipeline = ingestion(
        sessions,
        storage,
        FakeParser(tei(header='<idno type="DOI">not a doi</idno>', body=BODY)),
    )
    document_id = pipeline.register(upload()).document_id

    assert pipeline.process(document_id) == "parsed"
    with sessions() as session:
        paper = session.get(Paper, get_document(sessions, document_id).paper_id)
        assert paper is not None
        assert (paper.doi, paper.doi_normalized) == (None, None)


# --- process: failures -------------------------------------------------------------------


@pytest.mark.parametrize(
    "reason",
    [
        "parser_unreachable",
        "parser_busy",
        "unreadable_pdf",
        "no_text_layer",
        "empty_parse",
    ],
)
def test_parser_failure_marks_the_document_failed(
    sessions: sessionmaker[Session], storage: LocalStorage, reason: str
) -> None:
    pipeline = ingestion(
        sessions, storage, FakeParser(failure=ParserFailure(reason, "msg"))
    )
    document_id = pipeline.register(upload()).document_id

    assert pipeline.process(document_id) == "failed"

    document = get_document(sessions, document_id)
    assert (document.status, document.failure_reason, document.failure_message) == (
        "failed",
        reason,
        "msg",
    )
    assert document.paper_id is None
    assert document.tei_storage_key is None
    assert passages_of(sessions, document_id) == []
    assert storage.read(document.storage_key) == PDF  # original file kept (PRD §8.3)


@pytest.mark.parametrize(
    ("tei_bytes", "reason"),
    [
        (b"<not xml", "malformed_tei"),
        (tei(abstract=f"<div>{p('Only an abstract.')}</div>", body=""), "empty_parse"),
    ],
)
def test_unusable_tei_marks_the_document_failed_and_keeps_the_tei(
    sessions: sessionmaker[Session],
    storage: LocalStorage,
    tei_bytes: bytes,
    reason: str,
) -> None:
    pipeline = ingestion(sessions, storage, FakeParser(tei_bytes))
    document_id = pipeline.register(upload()).document_id

    assert pipeline.process(document_id) == "failed"

    document = get_document(sessions, document_id)
    assert document.failure_reason == reason
    assert document.tei_storage_key is not None
    assert storage.read(document.tei_storage_key) == tei_bytes  # kept for inspection
    assert passages_of(sessions, document_id) == []
    assert count(sessions, Paper) == 0


def test_tei_that_cannot_be_stored_is_a_storage_error(
    sessions: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = TeiStorageFails(tmp_path / "storage")
    pipeline = ingestion(sessions, storage, FakeParser(GOOD_TEI))
    document_id = pipeline.register(upload()).document_id

    assert pipeline.process(document_id) == "failed"
    assert get_document(sessions, document_id).failure_reason == "storage_error"
    assert count(sessions, Passage) == 0


def test_failure_in_the_final_transaction_stores_nothing(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    """Paper, passages and the parsed status are written together or not at all."""
    from app.services.ingestion.tei import parse_tei

    def parse_with_an_invalid_passage(raw: bytes) -> ParsedDocument:
        parsed = parse_tei(raw)
        bad = ParsedPassage(len(parsed.passages), "body", None, None, None, "x", 0, 0)
        return ParsedDocument(
            **{**parsed.__dict__, "passages": [*parsed.passages, bad]}
        )

    pipeline = ingestion(
        sessions, storage, FakeParser(GOOD_TEI), parse_with_an_invalid_passage
    )
    document_id = pipeline.register(upload()).document_id

    with pytest.raises(IntegrityError):
        pipeline.process(document_id)

    assert count(sessions, Paper) == 0
    assert count(sessions, Passage) == 0
    # Left processing; startup recovery marks it interrupted (FR-ING-010, P3-T7).
    assert get_document(sessions, document_id).status == "processing"


# --- state rules ---------------------------------------------------------------------------


def test_only_a_pending_document_can_be_processed(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    pipeline = ingestion(sessions, storage, FakeParser(GOOD_TEI))
    document_id = pipeline.register(upload()).document_id
    pipeline.process(document_id)

    with pytest.raises(DocumentStateError):
        pipeline.process(document_id)


def test_unknown_document_is_an_error(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    with pytest.raises(DocumentStateError):
        ingestion(sessions, storage, FakeParser()).process(uuid.uuid4())


# --- duplicates (P3-T6, FR-ING-008, AC-VS-04) ------------------------------------------


def stored_pdfs(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "storage").rglob("*.pdf"))


def test_identical_file_returns_the_existing_document_without_a_second_copy(
    sessions: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = CountingStorage(tmp_path / "storage")
    pipeline = ingestion(sessions, storage, FakeParser())

    first = pipeline.register(upload(name="a.pdf"))
    second = pipeline.register(upload(name="renamed copy.pdf"))

    assert first.created is True
    assert second.created is False
    assert second.document_id == first.document_id
    assert count(sessions, Document) == 1
    assert len(stored_pdfs(tmp_path)) == 1
    assert storage.pdf_saves == 1  # the duplicate was recognised before storing
    assert get_document(sessions, first.document_id).original_filename == "a.pdf"


def test_same_file_twice_gives_one_document_and_one_passage_set(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    """AC-VS-04."""
    pipeline = ingestion(sessions, storage, FakeParser(GOOD_TEI))
    first = pipeline.register(upload())
    pipeline.process(first.document_id)

    again = pipeline.register(upload())

    assert again.document_id == first.document_id
    assert again.created is False
    assert count(sessions, Document) == 1
    assert len(passages_of(sessions, first.document_id)) == 5
    assert count(sessions, Passage) == 5


def test_concurrent_identical_uploads_create_one_document(
    sessions: sessionmaker[Session], tmp_path: Path
) -> None:
    uploads = 6
    storage = CountingStorage(tmp_path / "storage", barrier=threading.Barrier(uploads))
    pipeline = ingestion(sessions, storage, FakeParser())

    with ThreadPoolExecutor(max_workers=uploads) as pool:
        results = list(pool.map(lambda _: pipeline.register(upload()), range(uploads)))

    assert storage.pdf_saves == uploads  # every upload really raced to the insert
    assert len({r.document_id for r in results}) == 1
    assert sum(r.created for r in results) == 1
    assert count(sessions, Document) == 1
    assert len(stored_pdfs(tmp_path)) == 1  # losers removed their copies


# --- retries (P3-T6) ---------------------------------------------------------------------


def test_failed_document_can_be_retried_and_then_parses(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    parser = FakeParser(failure=ParserFailure("parser_unreachable", "refused"))
    pipeline = ingestion(sessions, storage, parser)
    document_id = pipeline.register(upload()).document_id
    assert pipeline.process(document_id) == "failed"

    parser.failure = None
    parser.tei_bytes = GOOD_TEI
    assert pipeline.process(document_id) == "parsed"

    document = get_document(sessions, document_id)
    assert (document.failure_reason, document.failure_message) == (None, None)
    assert len(passages_of(sessions, document_id)) == 5
    assert parser.received == [PDF, PDF]


def test_retry_after_malformed_tei_replaces_the_tei_key(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    parser = FakeParser(b"<not xml")
    pipeline = ingestion(sessions, storage, parser)
    document_id = pipeline.register(upload()).document_id
    pipeline.process(document_id)
    failed_key = get_document(sessions, document_id).tei_storage_key

    parser.tei_bytes = GOOD_TEI
    pipeline.process(document_id)

    new_key = get_document(sessions, document_id).tei_storage_key
    assert new_key is not None and new_key != failed_key
    assert storage.read(new_key) == GOOD_TEI


@pytest.mark.parametrize("final_status", ["parsed"])
def test_parsed_document_cannot_be_processed_again(
    sessions: sessionmaker[Session], storage: LocalStorage, final_status: str
) -> None:
    pipeline = ingestion(sessions, storage, FakeParser(GOOD_TEI))
    document_id = pipeline.register(upload()).document_id
    assert pipeline.process(document_id) == final_status

    with pytest.raises(DocumentStateError):
        pipeline.process(document_id)
    assert len(passages_of(sessions, document_id)) == 5


def test_concurrent_processing_of_one_document_runs_once(
    sessions: sessionmaker[Session], storage: LocalStorage
) -> None:
    parser = FakeParser(GOOD_TEI)
    pipeline = ingestion(sessions, storage, parser)
    document_id = pipeline.register(upload()).document_id
    start = threading.Barrier(4)

    def process_at_once() -> str:
        start.wait()
        try:
            return pipeline.process(document_id)
        except DocumentStateError:
            return "refused"

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = sorted(pool.map(lambda _: process_at_once(), range(4)))

    assert outcomes == ["parsed", "refused", "refused", "refused"]
    assert len(parser.received) == 1
    assert len(passages_of(sessions, document_id)) == 5

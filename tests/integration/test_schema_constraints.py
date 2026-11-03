"""Constraint tests against PostgreSQL (P2-T5, docs/design/schema.md §9).

Every rejection test checks the name of the constraint PostgreSQL reports, so
a test cannot pass because some other rule failed. Each test runs in a
transaction that is rolled back.
"""

import hashlib
import itertools
import uuid
from typing import Any

import pytest
from sqlalchemy import Connection, delete, select, update
from sqlalchemy.exc import IntegrityError

from app.models import Base

_counter = itertools.count()

papers = Base.metadata.tables["papers"]
documents = Base.metadata.tables["documents"]
passages = Base.metadata.tables["passages"]


def unique_sha256() -> str:
    return hashlib.sha256(str(next(_counter)).encode()).hexdigest()


def add_paper(conn: Connection, **values: Any) -> uuid.UUID:
    row = {"metadata_source": "grobid", **values}
    new_id: uuid.UUID = conn.execute(
        papers.insert().values(row).returning(papers.c.id)
    ).scalar_one()
    return new_id


def add_document(conn: Connection, **values: Any) -> uuid.UUID:
    n = next(_counter)
    row = {
        "sha256": unique_sha256(),
        "size_bytes": 1000,
        "storage_key": f"pdf/{n}",
        **values,
    }
    new_id: uuid.UUID = conn.execute(
        documents.insert().values(row).returning(documents.c.id)
    ).scalar_one()
    return new_id


def add_parsed_document(
    conn: Connection, paper_id: uuid.UUID, **values: Any
) -> uuid.UUID:
    n = next(_counter)
    return add_document(
        conn,
        paper_id=paper_id,
        status="parsed",
        parser_name="grobid",
        parser_version="0.9.1",
        tei_storage_key=f"tei/{n}",
        **values,
    )


def add_passage(conn: Connection, document_id: uuid.UUID, **values: Any) -> uuid.UUID:
    row = {
        "document_id": document_id,
        "ordinal": next(_counter),
        "region": "body",
        "text": "Synthetic passage text.",
        **values,
    }
    new_id: uuid.UUID = conn.execute(
        passages.insert().values(row).returning(passages.c.id)
    ).scalar_one()
    return new_id


def rejected_by(conn: Connection, constraint: str, action: Any) -> None:
    """Run `action` in a savepoint; it must fail on exactly `constraint`."""
    with pytest.raises(IntegrityError) as error, conn.begin_nested():
        action()
    assert error.value.orig is not None
    assert error.value.orig.diag.constraint_name == constraint  # type: ignore[attr-defined]


# --- papers -------------------------------------------------------------------


def test_duplicate_normalised_doi_is_rejected(conn: Connection) -> None:
    add_paper(conn, doi="10.1/A", doi_normalized="10.1/a")
    rejected_by(
        conn,
        "uq_papers_doi_normalized",
        lambda: add_paper(conn, doi="doi:10.1/a", doi_normalized="10.1/a"),
    )


def test_many_papers_without_doi_are_allowed(conn: Connection) -> None:
    for _ in range(3):
        add_paper(conn)
    count = conn.execute(
        select(papers.c.id).where(papers.c.doi_normalized.is_(None))
    ).all()
    assert len(count) == 3


@pytest.mark.parametrize(
    ("values", "constraint"),
    [
        ({"doi": "10.1/a"}, "ck_papers_doi_pair"),
        ({"doi_normalized": "10.1/a"}, "ck_papers_doi_pair"),
        ({"doi": "x", "doi_normalized": "11.1/a"}, "ck_papers_doi_normalized_format"),
        ({"doi": ""}, "ck_papers_doi_not_empty"),
        ({"title": ""}, "ck_papers_title_not_empty"),
        ({"abstract": ""}, "ck_papers_abstract_not_empty"),
        ({"metadata_source": "crossref"}, "ck_papers_metadata_source_valid"),
    ],
)
def test_invalid_paper_rows_are_rejected(
    conn: Connection, values: dict[str, str], constraint: str
) -> None:
    rejected_by(conn, constraint, lambda: add_paper(conn, **values))


def test_paper_defaults(conn: Connection) -> None:
    paper_id = add_paper(conn)
    row = conn.execute(select(papers).where(papers.c.id == paper_id)).one()
    assert row.authors == []
    assert row.title is None
    assert row.created_at is not None
    assert paper_id.version == 7


# --- documents ----------------------------------------------------------------


def test_duplicate_file_hash_is_rejected(conn: Connection) -> None:
    sha = unique_sha256()
    add_document(conn, sha256=sha)
    rejected_by(conn, "uq_documents_sha256", lambda: add_document(conn, sha256=sha))


def test_two_documents_share_one_paper(conn: Connection) -> None:
    """Different files with the same DOI belong to one paper (PRD §8.3)."""
    paper_id = add_paper(conn, doi="10.1/x", doi_normalized="10.1/x")
    add_parsed_document(conn, paper_id)
    add_parsed_document(conn, paper_id)
    rows = conn.execute(
        select(documents.c.id).where(documents.c.paper_id == paper_id)
    ).all()
    assert len(rows) == 2


def test_document_for_unknown_paper_is_rejected(conn: Connection) -> None:
    rejected_by(
        conn,
        "fk_documents_paper_id_papers",
        lambda: add_document(conn, paper_id=uuid.uuid4()),
    )


@pytest.mark.parametrize(
    ("values", "constraint"),
    [
        ({"status": "done"}, "ck_documents_status_valid"),
        ({"status": "failed"}, "ck_documents_failure_reason_iff_failed"),
        ({"failure_reason": "empty_parse"}, "ck_documents_failure_reason_iff_failed"),
        (
            {"status": "failed", "failure_reason": "not_pdf"},
            "ck_documents_failure_reason_valid",
        ),
        ({"failure_message": "x"}, "ck_documents_failure_message_only_when_failed"),
        ({"status": "parsed"}, "ck_documents_parsed_is_complete"),
        ({"status": "processing"}, "ck_documents_processing_has_start"),
        ({"sha256": "A" * 64}, "ck_documents_sha256_format"),
        ({"sha256": "abc"}, "ck_documents_sha256_format"),
        ({"size_bytes": 0}, "ck_documents_size_positive"),
        ({"storage_key": ""}, "ck_documents_storage_key_not_empty"),
        ({"original_filename": ""}, "ck_documents_original_filename_length"),
        ({"page_count": 0}, "ck_documents_page_count_positive"),
        ({"skipped_paragraphs": -1}, "ck_documents_skipped_not_negative"),
    ],
)
def test_invalid_document_rows_are_rejected(
    conn: Connection, values: dict[str, Any], constraint: str
) -> None:
    rejected_by(conn, constraint, lambda: add_document(conn, **values))


def test_parsed_document_needs_its_tei_artifact(conn: Connection) -> None:
    paper_id = add_paper(conn)
    rejected_by(
        conn,
        "ck_documents_parsed_is_complete",
        lambda: add_document(
            conn,
            paper_id=paper_id,
            status="parsed",
            parser_name="grobid",
            parser_version="0.9.1",
        ),
    )


def test_new_document_defaults_to_pending(conn: Connection) -> None:
    document_id = add_document(conn)
    row = conn.execute(select(documents).where(documents.c.id == document_id)).one()
    assert row.status == "pending"
    assert row.paper_id is None
    assert document_id.version == 7


def test_paper_with_documents_cannot_be_deleted(conn: Connection) -> None:
    paper_id = add_paper(conn)
    add_parsed_document(conn, paper_id)
    rejected_by(
        conn,
        "fk_documents_paper_id_papers",
        lambda: conn.execute(delete(papers).where(papers.c.id == paper_id)),
    )


# --- passages -----------------------------------------------------------------


@pytest.fixture
def document_id(conn: Connection) -> uuid.UUID:
    return add_parsed_document(conn, add_paper(conn))


def test_duplicate_ordinal_in_one_document_is_rejected(
    conn: Connection, document_id: uuid.UUID
) -> None:
    add_passage(conn, document_id, ordinal=0)
    rejected_by(
        conn,
        "uq_passages_document_id_ordinal",
        lambda: add_passage(conn, document_id, ordinal=0),
    )


def test_same_ordinal_in_different_documents_is_allowed(conn: Connection) -> None:
    paper_id = add_paper(conn)
    add_passage(conn, add_parsed_document(conn, paper_id), ordinal=0)
    add_passage(conn, add_parsed_document(conn, paper_id), ordinal=0)


def test_passage_for_unknown_document_is_rejected(conn: Connection) -> None:
    rejected_by(
        conn,
        "fk_passages_document_id_documents",
        lambda: add_passage(conn, uuid.uuid4()),
    )


@pytest.mark.parametrize(
    ("values", "constraint"),
    [
        ({"region": "footnote"}, "ck_passages_region_valid"),
        ({"back_type": "annex"}, "ck_passages_back_type_only_for_back"),
        ({"region": "back", "back_type": ""}, "ck_passages_back_type_not_empty"),
        ({"text": ""}, "ck_passages_text_not_empty"),
        ({"section_title": ""}, "ck_passages_section_title_not_empty"),
        ({"section_number": ""}, "ck_passages_section_number_not_empty"),
        ({"page_start": 0, "page_end": 0}, "ck_passages_page_start_positive"),
        ({"page_start": 3, "page_end": 2}, "ck_passages_page_order"),
        ({"page_start": 3}, "ck_passages_pages_both_or_neither"),
        ({"page_end": 3}, "ck_passages_pages_both_or_neither"),
        ({"ordinal": -1}, "ck_passages_ordinal_not_negative"),
    ],
)
def test_invalid_passage_rows_are_rejected(
    conn: Connection, document_id: uuid.UUID, values: dict[str, Any], constraint: str
) -> None:
    rejected_by(conn, constraint, lambda: add_passage(conn, document_id, **values))


def test_unknown_page_is_stored_and_read_back_as_null(
    conn: Connection, document_id: uuid.UUID
) -> None:
    passage_id = add_passage(conn, document_id)
    row = conn.execute(select(passages).where(passages.c.id == passage_id)).one()
    assert row.page_start is None
    assert row.page_end is None


def test_back_matter_keeps_its_type(conn: Connection, document_id: uuid.UUID) -> None:
    passage_id = add_passage(conn, document_id, region="back", back_type="availability")
    assert (
        conn.execute(
            select(passages.c.back_type).where(passages.c.id == passage_id)
        ).scalar_one()
        == "availability"
    )


@pytest.mark.parametrize(
    ("number", "title", "expected"),
    [
        ("3.1", "Methods", "3.1 Methods"),
        (None, "Introduction", "Introduction"),
        (None, None, None),
    ],
)
def test_section_path_is_generated(
    conn: Connection,
    document_id: uuid.UUID,
    number: str | None,
    title: str | None,
    expected: str | None,
) -> None:
    passage_id = add_passage(
        conn, document_id, section_number=number, section_title=title
    )
    path = conn.execute(
        select(passages.c.section_path).where(passages.c.id == passage_id)
    ).scalar_one()
    assert path == expected


def test_passages_cannot_be_updated(conn: Connection, document_id: uuid.UUID) -> None:
    passage_id = add_passage(conn, document_id)
    with pytest.raises(IntegrityError) as error, conn.begin_nested():
        conn.execute(
            update(passages).where(passages.c.id == passage_id).values(text="changed")
        )
    assert "passages are immutable" in str(error.value.orig)
    assert error.value.orig is not None
    assert error.value.orig.sqlstate == "23001"  # type: ignore[attr-defined]


def test_document_with_passages_cannot_be_deleted(
    conn: Connection, document_id: uuid.UUID
) -> None:
    add_passage(conn, document_id)
    rejected_by(
        conn,
        "fk_passages_document_id_documents",
        lambda: conn.execute(delete(documents).where(documents.c.id == document_id)),
    )

"""Tests for upload validation (P3-T2, FR-ING-001, NFR-SEC-002).

All inputs are synthetic bytes; no paper content is used.
"""

import hashlib

import pytest

from app.services.ingestion.validation import (
    UploadRejectedError,
    display_filename,
    validate_upload,
)

LIMIT = 1000
PDF = b"%PDF-1.4\n%synthetic\n1 0 obj << >> endobj\n%%EOF\n"


def rejection_code(data: bytes, filename: str | None = "paper.pdf") -> str:
    with pytest.raises(UploadRejectedError) as error:
        validate_upload(data, filename, max_bytes=LIMIT)
    return error.value.code


# --- accepted -------------------------------------------------------------------


def test_valid_pdf_is_accepted_unmodified_with_hash_and_size() -> None:
    upload = validate_upload(PDF, "paper.pdf", max_bytes=LIMIT)

    assert upload.content == PDF
    assert upload.size_bytes == len(PDF)
    assert upload.sha256 == hashlib.sha256(PDF).hexdigest()
    assert upload.original_filename == "paper.pdf"


@pytest.mark.parametrize("version", [b"1.3", b"1.4", b"1.7", b"2.0"])
def test_pdf_versions_are_accepted(version: bytes) -> None:
    validate_upload(b"%PDF-" + version + b"\n...", "x.pdf", max_bytes=LIMIT)


def test_file_exactly_at_the_limit_is_accepted() -> None:
    data = PDF + b"0" * (LIMIT - len(PDF))

    assert validate_upload(data, None, max_bytes=LIMIT).size_bytes == LIMIT


def test_content_decides_not_the_filename() -> None:
    """A real PDF with a misleading name is still a PDF."""
    upload = validate_upload(PDF, "notes.txt", max_bytes=LIMIT)

    assert upload.original_filename == "notes.txt"


# --- rejected -------------------------------------------------------------------


def test_text_file_renamed_pdf_is_rejected() -> None:
    """The FR-ING-001 acceptance case."""
    assert rejection_code(b"This is a plain text file.\n", "paper.pdf") == "not_pdf"


@pytest.mark.parametrize(
    "data",
    [
        b"<!DOCTYPE html><html></html>",
        b"PK\x03\x04 zip or docx",
        b"%PDF",  # no dash
        b"%pdf-1.4 lower case",
        b"\xef\xbb\xbf%PDF-1.4 after a byte-order mark",
        b" %PDF-1.4 after a space",
    ],
)
def test_content_that_does_not_start_with_the_pdf_signature_is_rejected(
    data: bytes,
) -> None:
    assert rejection_code(data) == "not_pdf"


def test_empty_file_is_rejected() -> None:
    assert rejection_code(b"") == "empty_file"


def test_file_over_the_limit_is_rejected() -> None:
    assert rejection_code(PDF + b"0" * LIMIT) == "file_too_large"


def test_size_is_checked_before_the_signature() -> None:
    assert rejection_code(b"x" * (LIMIT + 1)) == "file_too_large"


def test_rejections_carry_a_plain_language_message_without_the_filename() -> None:
    """FR-UI-001; the client filename is never echoed back."""
    with pytest.raises(UploadRejectedError) as error:
        validate_upload(b"text", "<script>evil</script>.pdf", max_bytes=LIMIT)

    assert error.value.message
    assert "script" not in error.value.message
    assert "PDF" in error.value.message


def test_limit_must_be_positive() -> None:
    with pytest.raises(ValueError):
        validate_upload(PDF, None, max_bytes=0)


# --- display filename (never a path) ---------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("paper.pdf", "paper.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("C:\\Users\\someone\\Downloads\\paper.pdf", "paper.pdf"),
        ("folder/sub\\mixed.pdf", "mixed.pdf"),
        ("  spaced   out   name.pdf  ", "spaced out name.pdf"),
        ("tab\tand\nnewline.pdf", "tab and newline.pdf"),
        ("null\x00byte.pdf", "nullbyte.pdf"),
        ("Étude über Daten – 2024.pdf", "Étude über Daten – 2024.pdf"),
        (None, None),
        ("", None),
        ("   ", None),
        ("folder/", None),
        ("..", None),
        (".", None),
    ],
)
def test_display_filename(raw: str | None, expected: str | None) -> None:
    assert display_filename(raw) == expected


def test_long_filename_is_cut_to_the_database_limit() -> None:
    name = display_filename("a" * 300 + ".pdf")

    assert name is not None
    assert len(name) == 255

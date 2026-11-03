"""The GROBID client against the real local GROBID (P3-T3).

Inputs are tiny synthetic PDFs built here; no paper content is used.
"""

import pytest

from app.config import Settings
from app.services.ingestion.grobid import GrobidClient, ParserFailure

TEI_NAMESPACE = b"http://www.tei-c.org/ns/1.0"


def tiny_pdf(page_content: bytes) -> bytes:
    """A valid one-page PDF with Helvetica and the given content stream."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(page_content)
        + page_content
        + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


TEXT_PAGE = tiny_pdf(
    b"BT /F1 12 Tf 72 720 Td (A synthetic sentence for the parser test.) Tj ET"
)
BLANK_PAGE = tiny_pdf(b"")


@pytest.fixture
def client(grobid_url: str, settings: Settings) -> GrobidClient:
    return GrobidClient(
        grobid_url,
        timeout_seconds=settings.grobid_timeout_seconds,
        busy_retries=settings.grobid_busy_retries,
        busy_retry_seconds=settings.grobid_busy_retry_seconds,
    )


def test_a_pdf_returns_tei(client: GrobidClient) -> None:
    tei = client.process_fulltext(TEXT_PAGE)

    assert tei.lstrip().startswith(b"<?xml")
    assert TEI_NAMESPACE in tei


def test_not_a_pdf_is_an_unreadable_pdf(client: GrobidClient) -> None:
    with pytest.raises(ParserFailure) as error:
        client.process_fulltext(b"This is a plain text file, not a PDF.")

    assert error.value.reason == "unreadable_pdf"


def test_a_page_without_text_has_no_text_layer(client: GrobidClient) -> None:
    with pytest.raises(ParserFailure) as error:
        client.process_fulltext(BLANK_PAGE)

    assert error.value.reason == "no_text_layer"


def test_nothing_listening_is_unreachable(settings: Settings) -> None:
    client = GrobidClient(
        "http://127.0.0.1:9",  # discard port: nothing listens there locally
        timeout_seconds=5.0,
        busy_retries=0,
        busy_retry_seconds=0.0,
    )

    with pytest.raises(ParserFailure) as error:
        client.process_fulltext(TEXT_PAGE)

    assert error.value.reason == "parser_unreachable"

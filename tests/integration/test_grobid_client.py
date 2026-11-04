"""The GROBID client against the real local GROBID (P3-T3).

Inputs are tiny synthetic PDFs (tests/synthetic.py); no paper content is used.
"""

import pytest
from tests.synthetic import BLANK_PAGE_PDF as BLANK_PAGE
from tests.synthetic import TEXT_PAGE_PDF as TEXT_PAGE

from app.config import Settings
from app.services.ingestion.grobid import GrobidClient, ParserFailure

TEI_NAMESPACE = b"http://www.tei-c.org/ns/1.0"


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

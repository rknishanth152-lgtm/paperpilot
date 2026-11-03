"""Tests for the GROBID client against a stub server (P3-T3).

httpx.MockTransport plays GROBID, so these tests are offline. Mapping follows
docs/design/parser-output.md §7, built from the Phase 1 observations.
"""

from collections.abc import Callable

import httpx
import pytest

from app.services.ingestion.grobid import (
    GROBID_FORM_FIELDS,
    GrobidClient,
    ParserFailure,
)

PDF = b"%PDF-1.4 synthetic"
TEI = b'<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"/>'

Handler = Callable[[httpx.Request], httpx.Response]


class Sleeps:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def make_client(
    handler: Handler,
    *,
    retries: int = 2,
    wait: float = 5.0,
    sleeps: Sleeps | None = None,
) -> GrobidClient:
    return GrobidClient(
        "http://grobid.test",
        timeout_seconds=30.0,
        busy_retries=retries,
        busy_retry_seconds=wait,
        transport=httpx.MockTransport(handler),
        sleep=sleeps or Sleeps(),
    )


def reason(handler: Handler, **kwargs: object) -> str:
    with pytest.raises(ParserFailure) as error:
        make_client(handler, **kwargs).process_fulltext(PDF)  # type: ignore[arg-type]
    return error.value.reason


# --- the request ------------------------------------------------------------------


def test_request_sends_the_pdf_with_the_fixed_privacy_safe_options() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=TEI)

    assert make_client(handler).process_fulltext(PDF) == TEI

    request = seen[0]
    body = request.read()
    assert request.method == "POST"
    assert request.url.path == "/api/processFulltextDocument"
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert PDF in body
    assert b'name="input"' in body
    assert b'name="consolidateHeader"\r\n\r\n0' in body
    assert b'name="consolidateCitations"\r\n\r\n0' in body
    assert b'name="consolidateFunders"\r\n\r\n0' in body
    assert body.count(b'name="teiCoordinates"') == 4
    assert b"generateIDs" not in body


def test_form_fields_never_enable_consolidation() -> None:
    """Consolidation would send paper metadata to CrossRef (Phase 1, §2.3)."""
    for field in ("consolidateHeader", "consolidateCitations", "consolidateFunders"):
        assert GROBID_FORM_FIELDS[field] == "0"


def test_parser_config_records_what_was_sent() -> None:
    client = make_client(lambda request: httpx.Response(200, content=TEI))

    assert client.parser_config == {
        "endpoint": "/api/processFulltextDocument",
        "form_fields": GROBID_FORM_FIELDS,
    }


# --- responses ----------------------------------------------------------------------


def test_204_no_content_is_an_empty_parse() -> None:
    assert reason(lambda r: httpx.Response(204)) == "empty_parse"


def test_200_with_empty_body_is_an_empty_parse() -> None:
    assert reason(lambda r: httpx.Response(200, content=b"")) == "empty_parse"


@pytest.mark.parametrize(
    ("grobid_code", "expected"),
    [
        ("BAD_INPUT_DATA", "unreadable_pdf"),
        ("NO_BLOCKS", "no_text_layer"),
        ("TOO_MANY_TOKENS", "document_too_long"),
        ("TOO_MANY_BLOCKS", "document_too_long"),
        ("TIMEOUT", "parser_timeout"),
        ("TAGGING_ERROR", "parser_error"),
        ("PDFALTO_CONVERSION_FAILURE", "parser_error"),
        ("GENERAL", "parser_error"),
    ],
)
def test_500_codes_map_to_failure_reasons(grobid_code: str, expected: str) -> None:
    body = f"[{grobid_code}] something went wrong"
    assert reason(lambda r: httpx.Response(500, text=body)) == expected


def test_500_without_a_code_is_a_parser_error() -> None:
    assert (
        reason(lambda r: httpx.Response(500, text="Internal error")) == "parser_error"
    )


@pytest.mark.parametrize("status", [400, 404, 405, 502])
def test_other_statuses_are_parser_errors(status: int) -> None:
    assert reason(lambda r: httpx.Response(status, text="x")) == "parser_error"


def test_failure_message_has_code_and_status_but_not_the_body() -> None:
    body = "[BAD_INPUT_DATA] PDF to XML conversion failed with error code: 1 /some/path"

    with pytest.raises(ParserFailure) as error:
        make_client(lambda r: httpx.Response(500, text=body)).process_fulltext(PDF)

    assert "BAD_INPUT_DATA" in error.value.message
    assert "500" in error.value.message
    assert "/some/path" not in error.value.message
    assert len(error.value.message) <= 1000


# --- busy (503) and retries -----------------------------------------------------------


def test_503_is_retried_and_can_then_succeed() -> None:
    responses = iter(
        [
            httpx.Response(503, text="<html>busy</html>"),
            httpx.Response(200, content=TEI),
        ]
    )
    sleeps = Sleeps()

    result = make_client(lambda r: next(responses), sleeps=sleeps).process_fulltext(PDF)

    assert result == TEI
    assert sleeps.calls == [5.0]


def test_503_after_all_retries_is_parser_busy() -> None:
    calls: list[int] = []
    sleeps = Sleeps()

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503, text="<html>busy</html>")

    assert reason(handler, retries=2, wait=7.0, sleeps=sleeps) == "parser_busy"
    assert len(calls) == 3  # first try + 2 retries
    assert sleeps.calls == [7.0, 7.0]


def test_zero_retries_means_one_attempt() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503)

    assert reason(handler, retries=0) == "parser_busy"
    assert len(calls) == 1


# --- transport failures -----------------------------------------------------------------


def raising(exc: Exception) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    return handler


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (httpx.ConnectError("refused"), "parser_unreachable"),
        (httpx.ConnectTimeout("connect timeout"), "parser_unreachable"),
        (httpx.RemoteProtocolError("Server disconnected"), "parser_disconnected"),
        (httpx.ReadError("connection reset"), "parser_disconnected"),
        (httpx.ReadTimeout("read timeout"), "parser_timeout"),
        (httpx.WriteTimeout("write timeout"), "parser_timeout"),
    ],
)
def test_transport_failures_map_to_failure_reasons(
    exc: Exception, expected: str
) -> None:
    assert reason(raising(exc)) == expected


def test_transport_failures_are_not_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ConnectError("refused")

    assert reason(handler) == "parser_unreachable"
    assert len(calls) == 1


def test_every_reason_is_a_stored_failure_reason() -> None:
    """Reasons must satisfy the documents.failure_reason CHECK constraint."""
    from app.models.constraints import FAILURE_REASONS
    from app.services.ingestion.grobid import REASONS_USED

    assert set(REASONS_USED) <= set(FAILURE_REASONS)

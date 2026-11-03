"""GROBID client (P3-T3, FR-ING-003, FR-ING-004, NFR-REL-003).

Sends a stored PDF to GROBID's full-text endpoint with a fixed, privacy-safe
request and turns every failure into one `failure_reason` from
docs/design/parser-output.md §7. The mapping comes from what GROBID 0.9.1 did
in the Phase 1 experiment (docs/experiments/grobid-feasibility.md §6).
"""

import re
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.config import Settings

ENDPOINT = "/api/processFulltextDocument"

# Fixed request (docs/design/parser-output.md §2). Consolidation stays off:
# GROBID's default would send extracted paper metadata to CrossRef.
GROBID_FORM_FIELDS: dict[str, str | list[str]] = {
    "consolidateHeader": "0",
    "consolidateCitations": "0",
    "consolidateFunders": "0",
    "includeRawCitations": "1",
    "teiCoordinates": ["p", "head", "figure", "biblStruct"],
}

# GROBID's error code in a 500 body, for example "[NO_BLOCKS] ...".
_GROBID_CODE = re.compile(r"^\[([A-Z_]+)\]")
_CODE_TO_REASON = {
    "BAD_INPUT_DATA": "unreadable_pdf",
    "NO_BLOCKS": "no_text_layer",
    "TOO_MANY_TOKENS": "document_too_long",
    "TOO_MANY_BLOCKS": "document_too_long",
    "TIMEOUT": "parser_timeout",
}

REASONS_USED = (
    "parser_unreachable",
    "parser_disconnected",
    "parser_timeout",
    "parser_busy",
    "unreadable_pdf",
    "no_text_layer",
    "document_too_long",
    "parser_error",
    "empty_parse",
)


class ParserFailure(Exception):
    """GROBID did not return usable TEI. `reason` is a stored failure_reason."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(f"{reason}: {message}")
        self.reason = reason
        self.message = message


class GrobidClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float,
        busy_retries: int,
        busy_retry_seconds: float,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._url = base_url.rstrip("/") + ENDPOINT
        self._timeout = httpx.Timeout(timeout_seconds)
        self._busy_retries = busy_retries
        self._busy_retry_seconds = busy_retry_seconds
        self._transport = transport
        self._sleep = sleep

    @classmethod
    def from_settings(cls, settings: Settings) -> GrobidClient:
        return cls(
            str(settings.grobid_url),
            timeout_seconds=settings.grobid_timeout_seconds,
            busy_retries=settings.grobid_busy_retries,
            busy_retry_seconds=settings.grobid_busy_retry_seconds,
        )

    @property
    def parser_config(self) -> dict[str, Any]:
        """What is sent, recorded with each document (DR-005)."""
        return {"endpoint": ENDPOINT, "form_fields": GROBID_FORM_FIELDS}

    def process_fulltext(self, pdf: bytes) -> bytes:
        """Return GROBID's TEI for `pdf`, or raise ParserFailure."""
        with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
            for attempt in range(self._busy_retries + 1):
                response = self._post(client, pdf)
                if response.status_code != 503:
                    return self._result(response)
                if attempt < self._busy_retries:
                    self._sleep(self._busy_retry_seconds)
        raise ParserFailure(
            "parser_busy",
            f"GROBID was busy (HTTP 503) after {self._busy_retries + 1} attempts",
        )

    def _post(self, client: httpx.Client, pdf: bytes) -> httpx.Response:
        try:
            return client.post(
                self._url,
                data=GROBID_FORM_FIELDS,
                files={"input": ("document.pdf", pdf, "application/pdf")},
            )
        except httpx.ConnectError as exc:
            raise _transport_failure("parser_unreachable", exc) from None
        except httpx.ConnectTimeout as exc:
            raise _transport_failure("parser_unreachable", exc) from None
        except httpx.TimeoutException as exc:
            raise _transport_failure("parser_timeout", exc) from None
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError) as exc:
            raise _transport_failure("parser_disconnected", exc) from None
        except httpx.TransportError as exc:
            raise _transport_failure("parser_error", exc) from None

    @staticmethod
    def _result(response: httpx.Response) -> bytes:
        status = response.status_code
        if status == 200 and response.content:
            return response.content
        if status in (200, 204):
            raise ParserFailure(
                "empty_parse", f"GROBID returned no content (HTTP {status})"
            )
        if status == 500:
            match = _GROBID_CODE.match(response.text)
            code = match.group(1) if match else "unknown"
            reason = _CODE_TO_REASON.get(code, "parser_error")
            raise ParserFailure(reason, f"GROBID error {code} (HTTP 500)")
        raise ParserFailure("parser_error", f"GROBID returned HTTP {status}")


def _transport_failure(reason: str, exc: Exception) -> ParserFailure:
    # Only the exception type: messages can contain addresses.
    return ParserFailure(reason, f"GROBID request failed ({type(exc).__name__})")

"""Error envelope and failure explanations without a database (P3-T8, NFR-SEC-005)."""

import asyncio

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.api.documents import read_limited
from app.main import create_app
from app.models.constraints import FAILURE_REASONS
from app.services.ingestion.explanations import FAILURE_EXPLANATIONS
from app.services.ingestion.validation import UploadRejectedError


def test_every_failure_reason_has_an_explanation() -> None:
    assert set(FAILURE_EXPLANATIONS) == set(FAILURE_REASONS)
    assert all(text.strip() for text in FAILURE_EXPLANATIONS.values())


def test_unknown_address_uses_the_error_envelope() -> None:
    response = TestClient(create_app()).get("/no-such-route")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "There is nothing at this address."}
    }


def test_wrong_method_uses_the_error_envelope() -> None:
    response = TestClient(create_app()).delete("/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


# --- Bounded upload reading (P3-T8) ------------------------------------------


def request_with_chunks(chunks: list[bytes], received: list[int]) -> Request:
    """A Request whose body arrives in `chunks`; `received` counts reads."""
    remaining = list(chunks)

    async def receive() -> dict[str, object]:
        received.append(1)
        chunk = remaining.pop(0)
        return {"type": "http.request", "body": chunk, "more_body": bool(remaining)}

    return Request({"type": "http", "method": "POST", "headers": []}, receive)


def test_read_limited_stops_at_the_first_chunk_over_the_limit() -> None:
    received: list[int] = []
    request = request_with_chunks([b"x" * 10] * 100, received)

    with pytest.raises(UploadRejectedError, match="file_too_large"):
        asyncio.run(read_limited(request, max_bytes=25))

    assert len(received) == 3  # 10, 20, 30 > 25: the other 97 chunks are never read


def test_read_limited_returns_the_whole_body_within_the_limit() -> None:
    request = request_with_chunks([b"ab", b"cd", b""], [])

    assert asyncio.run(read_limited(request, max_bytes=4)) == b"abcd"

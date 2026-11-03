"""Fixtures for tests that talk to the local services in compose.yaml.

These tests use the developer's real `.env`. If a service is not running they
fail with instructions instead of being skipped, so a missing service is never
mistaken for a passing run.
"""

import httpx
import pytest

from app.config import Settings, get_settings

START_SERVICES = "Start the services with `docker compose up -d --wait`."


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def grobid_url(settings: Settings) -> str:
    url = str(settings.grobid_url).rstrip("/")
    try:
        httpx.get(f"{url}/api/isalive", timeout=5.0)
    except httpx.TransportError as exc:
        pytest.fail(
            f"GROBID is not reachable at {url} ({type(exc).__name__}). {START_SERVICES}"
        )
    return url

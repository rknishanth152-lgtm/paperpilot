"""The local GROBID service is running and is the pinned version."""

import httpx

# Must match the image tag in compose.yaml.
EXPECTED_GROBID_VERSION = "0.9.1"


def test_grobid_is_alive(grobid_url: str) -> None:
    response = httpx.get(f"{grobid_url}/api/isalive", timeout=5.0)

    assert response.status_code == 200
    assert response.text.strip() == "true"


def test_grobid_is_the_pinned_version(grobid_url: str) -> None:
    response = httpx.get(f"{grobid_url}/api/version", timeout=5.0)

    assert response.status_code == 200
    assert response.json()["version"] == EXPECTED_GROBID_VERSION

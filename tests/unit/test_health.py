"""Smoke tests for the application entry point and the health route.

Settings are replaced so the tests never read the developer's `.env`.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.main
from app.config import Settings


def test_health_returns_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app.main,
        "get_settings",
        lambda: Settings(_env_file=None, postgres_password="pw"),
    )

    with TestClient(app.main.create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_fails_without_valid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setattr(app.main, "get_settings", lambda: Settings(_env_file=None))

    with (
        pytest.raises(ValidationError, match="postgres_password"),
        TestClient(app.main.create_app()),
    ):
        pass

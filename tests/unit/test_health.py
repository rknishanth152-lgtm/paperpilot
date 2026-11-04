"""Smoke tests for the application entry point and the health route.

Settings and startup recovery are replaced so the tests never read the
developer's `.env` or need a database.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.main
from app.config import Settings


@pytest.fixture
def recoveries(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Valid settings and a recorded, database-free startup recovery."""
    calls: list[int] = []
    monkeypatch.setattr(
        app.main,
        "get_settings",
        lambda: Settings(_env_file=None, postgres_password="pw"),
    )
    monkeypatch.setattr(app.main, "recover_on_startup", lambda: calls.append(1))
    return calls


def test_health_returns_ok(recoveries: list[int]) -> None:
    with TestClient(app.main.create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_runs_recovery_once(recoveries: list[int]) -> None:
    """FR-ING-010: interrupted documents are recovered when the server starts."""
    with TestClient(app.main.create_app()):
        pass

    assert recoveries == [1]


def test_startup_fails_if_recovery_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """No silent start with documents stuck in `processing`."""
    monkeypatch.setattr(
        app.main,
        "get_settings",
        lambda: Settings(_env_file=None, postgres_password="pw"),
    )

    def fail() -> None:
        raise ConnectionError("database unreachable (simulated)")

    monkeypatch.setattr(app.main, "recover_on_startup", fail)

    with pytest.raises(ConnectionError), TestClient(app.main.create_app()):
        pass


def test_startup_fails_without_valid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setattr(app.main, "get_settings", lambda: Settings(_env_file=None))

    with (
        pytest.raises(ValidationError, match="postgres_password"),
        TestClient(app.main.create_app()),
    ):
        pass

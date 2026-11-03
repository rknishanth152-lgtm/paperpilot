"""Tests for backend/app/config.py.

Each test isolates itself from the developer's real `.env` and environment
variables, so results do not depend on the machine.
"""

import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.config import REPO_ROOT, Settings

SETTING_NAMES = [name.upper() for name in Settings.model_fields]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)


def make_settings(**values: Any) -> Settings:
    """Settings from explicit values only, ignoring any `.env` file."""
    return Settings(_env_file=None, **values)


def test_defaults_need_only_a_password() -> None:
    settings = make_settings(postgres_password="pw")

    assert settings.postgres_host == "127.0.0.1"
    assert settings.postgres_port == 5432
    assert str(settings.grobid_url) == "http://127.0.0.1:8070/"
    assert settings.storage_dir == REPO_ROOT / "data" / "storage"
    assert settings.max_upload_bytes == 50 * 1024 * 1024
    assert settings.llm_provider is None
    assert settings.llm_api_key is None


def test_missing_password_is_rejected() -> None:
    with pytest.raises(ValidationError, match="postgres_password"):
        make_settings()


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        make_settings(postgres_password="")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("postgres_port", 0),
        ("postgres_port", 70000),
        ("grobid_url", "not a url"),
        ("grobid_timeout_seconds", 0),
        ("max_upload_mb", 0),
        ("postgres_db", ""),
    ],
)
def test_invalid_values_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError, match=field):
        make_settings(postgres_password="pw", **{field: value})


def test_password_is_hidden_when_printed() -> None:
    settings = make_settings(postgres_password="very-secret", llm_api_key="key-123")

    shown = repr(settings) + str(settings)
    assert "very-secret" not in shown
    assert "key-123" not in shown


def test_database_url_escapes_special_characters() -> None:
    settings = make_settings(postgres_password="p@ss:w/rd", postgres_user="a b")

    assert settings.database_url() == (
        "postgresql+psycopg://a%20b:p%40ss%3Aw%2Frd@127.0.0.1:5432/paperpilot"
    )


def test_absolute_storage_dir_is_kept(tmp_path: Path) -> None:
    settings = make_settings(postgres_password="pw", storage_dir=tmp_path)

    assert settings.storage_dir == tmp_path


def test_values_are_read_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_PASSWORD=from-file\n"
        "MAX_UPLOAD_MB=20\n"
        "GROBID_PORT=8070\n"  # Compose-only key: ignored by the backend
        "LLM_API_KEY=\n",  # blank means not set
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.postgres_password.get_secret_value() == "from-file"
    assert settings.max_upload_mb == 20
    assert settings.llm_api_key is None


def test_environment_variables_override_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("POSTGRES_PASSWORD=from-file\n", encoding="utf-8")
    monkeypatch.setenv("POSTGRES_PASSWORD", "from-env")

    settings = Settings(_env_file=env_file)

    assert settings.postgres_password.get_secret_value() == "from-env"


def test_env_example_lists_every_setting() -> None:
    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    keys = set(re.findall(r"^([A-Z_]+)=", example, flags=re.MULTILINE))

    missing = [name for name in SETTING_NAMES if name not in keys]
    assert missing == []

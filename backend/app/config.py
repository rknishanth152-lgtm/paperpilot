"""Application settings, loaded from the environment and `.env` in one place.

Nothing else in the application reads environment variables directly. Every
setting has a placeholder in `.env.example` (CLAUDE.md §5).
"""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Validated settings. Invalid or missing values fail at startup."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        # `.env` is shared with Docker Compose, which has keys the app does
        # not use (for example GROBID_PORT), so unknown keys are ignored.
        extra="ignore",
        # A blank value such as `LLM_API_KEY=` means "not set", not "".
        env_ignore_empty=True,
    )

    # PostgreSQL. The same POSTGRES_* values configure compose.yaml, so the
    # password is written once.
    postgres_host: str = Field(default="127.0.0.1", min_length=1)
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = Field(default="paperpilot", min_length=1)
    postgres_user: str = Field(default="paperpilot", min_length=1)
    postgres_password: SecretStr

    # GROBID (NFR-REL-003). The timeout is a placeholder until parse times
    # are measured in Phase 1.
    grobid_url: HttpUrl = HttpUrl("http://127.0.0.1:8070")
    grobid_timeout_seconds: float = Field(default=120.0, gt=0)

    # Local file storage (AD-002). Relative paths are resolved against the
    # repository root; the default lives in the git-ignored data/ folder.
    storage_dir: Path = Path("data/storage")

    # Upload limit (FR-ING-001). Placeholder until OQ-005 is answered in Phase 1.
    max_upload_mb: int = Field(default=50, gt=0)

    # LLM provider (OQ-011, decided in Phase 5). Unused until then.
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None

    @field_validator("postgres_password")
    @classmethod
    def password_not_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("POSTGRES_PASSWORD must not be empty")
        return value

    @field_validator("storage_dir")
    @classmethod
    def resolve_storage_dir(cls, value: Path) -> Path:
        return value if value.is_absolute() else REPO_ROOT / value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def database_url(self) -> str:
        """SQLAlchemy URL for psycopg 3. Contains the password: never log it."""
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password.get_secret_value(), safe="")
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Settings for the running application, loaded once."""
    return Settings()

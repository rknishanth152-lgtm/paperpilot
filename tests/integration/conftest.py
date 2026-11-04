"""Fixtures for tests that talk to the local services in compose.yaml.

These tests use the developer's real `.env`. If a service is not running they
fail with instructions instead of being skipped, so a missing service is never
mistaken for a passing run.

Schema tests never touch the development database: they create a throwaway
database on the same server, migrate it with Alembic, and drop it afterwards.
"""

from collections.abc import Iterator

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.config import REPO_ROOT, Settings, get_settings
from app.database import get_engine

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


@pytest.fixture(scope="session")
def db_engine(settings: Settings) -> Engine:
    engine = get_engine()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        # Only the error type: the message could include connection details.
        where = f"{settings.postgres_host}:{settings.postgres_port}"
        pytest.fail(
            f"PostgreSQL is not reachable at {where} ({type(exc.orig).__name__}). {START_SERVICES}"
        )
    return engine


# --- Throwaway databases for schema tests -----------------------------------


def alembic_config() -> Config:
    return Config(toml_file=str(REPO_ROOT / "pyproject.toml"))


def run_alembic(engine: Engine, action: str, target: str) -> None:
    """Run `alembic upgrade/downgrade <target>` on `engine`'s database."""
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        getattr(command, action)(config, target)


def create_database(settings: Settings, name: str) -> Engine:
    """(Re)create an empty database `name` and return an engine for it."""
    if name == settings.postgres_db:
        raise RuntimeError("refusing to recreate the development database")
    admin = create_engine(
        settings.model_copy(update={"postgres_db": "postgres"}).database_url(),
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()
    return create_engine(
        settings.model_copy(update={"postgres_db": name}).database_url()
    )


def drop_database(settings: Settings, engine: Engine, name: str) -> None:
    engine.dispose()
    admin = create_engine(
        settings.model_copy(update={"postgres_db": "postgres"}).database_url(),
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture(scope="session")
def schema_engine(db_engine: Engine, settings: Settings) -> Iterator[Engine]:
    """A fresh database migrated to the latest revision, for the whole session."""
    name = f"{settings.postgres_db}_test"
    engine = create_database(settings, name)
    try:
        run_alembic(engine, "upgrade", "head")
        yield engine
    finally:
        drop_database(settings, engine, name)


@pytest.fixture
def conn(schema_engine: Engine) -> Iterator[Connection]:
    """A connection in a transaction that is always rolled back after the test."""
    with schema_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.fixture
def sessions(schema_engine: Engine) -> Iterator[sessionmaker[Session]]:
    """Sessions on the throwaway database for code that commits its own work.

    Tables are emptied after each test. TRUNCATE does not fire the passage
    UPDATE trigger, so immutability is unaffected.
    """
    yield sessionmaker(bind=schema_engine, expire_on_commit=False)
    with schema_engine.begin() as connection:
        connection.execute(text("TRUNCATE passages, documents, papers"))

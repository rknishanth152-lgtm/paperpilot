"""Engine and session handling (AD-012: SQLAlchemy 2.x, psycopg 3, synchronous).

The engine is created on first use, not at import, so importing the app never
opens a database connection and tests can run without PostgreSQL.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """The application's engine, created once from the settings."""
    return create_engine(
        get_settings().database_url(),
        # Check a pooled connection before use, so a restarted PostgreSQL
        # gives a fresh connection instead of an error.
        pool_pre_ping=True,
    )


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """One unit of work: commit on success, roll back on any error."""
    session = _session_factory()()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, in one transaction."""
    with session_scope() as session:
        yield session

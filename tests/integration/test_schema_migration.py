"""The first migration applies to an empty database and can be reversed (P2-T5)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, inspect, text
from tests.integration.conftest import create_database, drop_database, run_alembic

from app.config import Settings

CORE_TABLES = {"papers", "documents", "passages"}
HEAD = "d2ea199dd3d3"


@pytest.fixture
def empty_engine(db_engine: Engine, settings: Settings) -> Iterator[Engine]:
    name = f"{settings.postgres_db}_test_migration"
    engine = create_database(settings, name)
    try:
        yield engine
    finally:
        drop_database(settings, engine, name)


def tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def test_migration_applies_to_an_empty_database(empty_engine: Engine) -> None:
    assert tables(empty_engine) == set()

    run_alembic(empty_engine, "upgrade", "head")

    assert CORE_TABLES <= tables(empty_engine)
    with empty_engine.connect() as connection:
        version = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    assert version == HEAD


def test_downgrade_removes_everything_and_upgrade_restores_it(
    empty_engine: Engine,
) -> None:
    run_alembic(empty_engine, "upgrade", "head")

    run_alembic(empty_engine, "downgrade", "base")
    assert tables(empty_engine) == {"alembic_version"}
    with empty_engine.connect() as connection:
        functions = connection.execute(
            text(
                "SELECT count(*) FROM pg_proc WHERE proname = 'passages_forbid_update'"
            )
        ).scalar_one()
    assert functions == 0

    run_alembic(empty_engine, "upgrade", "head")
    assert CORE_TABLES <= tables(empty_engine)

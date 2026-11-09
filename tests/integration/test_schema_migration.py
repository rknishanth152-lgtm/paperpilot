"""The first migration applies to an empty database and can be reversed (P2-T5)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DBAPIError
from tests.integration.conftest import create_database, drop_database, run_alembic

from app.config import Settings

CORE_TABLES = {"papers", "documents", "passages"}
BEFORE_SEARCH = "d2ea199dd3d3"
AFTER_SEARCH = "e3ab5ad233d7"
AFTER_EMBEDDINGS = "f4a9c1d27b60"
HEAD = "a7d3e5f1c829"


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


def passage_columns(engine: Engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("passages")}


def passage_indexes(engine: Engine) -> set[str]:
    return {str(index["name"]) for index in inspect(engine).get_indexes("passages")}


def test_search_migration_covers_existing_passages_and_reverses(
    empty_engine: Engine,
) -> None:
    """P4-T2: passages stored before the column exists become searchable."""
    run_alembic(empty_engine, "upgrade", BEFORE_SEARCH)
    body = "The experiments replicated earlier studies."
    with empty_engine.begin() as connection:
        document_id = connection.execute(
            text(
                "INSERT INTO documents (sha256, size_bytes, storage_key) "
                "VALUES (repeat('a', 64), 10, 'pdf/a') RETURNING id"
            )
        ).scalar_one()
        passage_id = connection.execute(
            text(
                "INSERT INTO passages (document_id, ordinal, region, text) "
                "VALUES (:d, 0, 'body', :t) RETURNING id"
            ),
            {"d": document_id, "t": body},
        ).scalar_one()

    run_alembic(empty_engine, "upgrade", AFTER_SEARCH)

    with empty_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT text, search_vector @@ plainto_tsquery('english', 'replication') "
                "FROM passages WHERE id = :id"
            ),
            {"id": passage_id},
        ).one()
    assert tuple(row) == (body, True)
    with (
        pytest.raises(DBAPIError, match="immutable"),
        empty_engine.begin() as connection,
    ):
        connection.execute(text("UPDATE passages SET ordinal = 1"))

    run_alembic(empty_engine, "downgrade", "-1")

    assert "search_vector" not in passage_columns(empty_engine)
    assert "ix_passages_search_vector" not in passage_indexes(empty_engine)
    with empty_engine.connect() as connection:
        kept = connection.execute(text("SELECT text FROM passages")).scalar_one()
        version = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    assert (kept, version) == (body, BEFORE_SEARCH)


def test_embeddings_migration_adds_the_table_and_reverses(empty_engine: Engine) -> None:
    """R2: enabling pgvector and the new table leave passages alone."""
    run_alembic(empty_engine, "upgrade", AFTER_SEARCH)
    with empty_engine.begin() as connection:
        document_id = connection.execute(
            text(
                "INSERT INTO documents (sha256, size_bytes, storage_key) "
                "VALUES (repeat('a', 64), 10, 'pdf/a') RETURNING id"
            )
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO passages (document_id, ordinal, region, text) "
                "VALUES (:d, 0, 'body', 'Kept.')"
            ),
            {"d": document_id},
        )

    run_alembic(empty_engine, "upgrade", AFTER_EMBEDDINGS)

    assert "passage_embeddings" in tables(empty_engine)
    assert extension_count(empty_engine) == 1

    run_alembic(empty_engine, "downgrade", "-1")

    assert "passage_embeddings" not in tables(empty_engine)
    assert extension_count(empty_engine) == 0
    with empty_engine.connect() as connection:
        kept = connection.execute(text("SELECT text FROM passages")).scalar_one()
    assert kept == "Kept."


def extension_count(engine: Engine) -> int:
    with engine.connect() as connection:
        count: int = connection.execute(
            text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()
    return count


ASSESSMENT_TABLES = {
    "reproducibility_assessments",
    "reproducibility_items",
    "reproducibility_item_passages",
}


def test_assessment_migration_adds_the_tables_and_reverses(
    empty_engine: Engine,
) -> None:
    """R5: the new tables can be removed again."""
    run_alembic(empty_engine, "upgrade", AFTER_EMBEDDINGS)
    assert not ASSESSMENT_TABLES & tables(empty_engine)

    run_alembic(empty_engine, "upgrade", "head")
    assert ASSESSMENT_TABLES <= tables(empty_engine)

    run_alembic(empty_engine, "downgrade", "-1")
    assert not ASSESSMENT_TABLES & tables(empty_engine)
    assert "passage_embeddings" in tables(empty_engine)

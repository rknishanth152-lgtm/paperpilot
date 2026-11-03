"""The configured PostgreSQL is reachable through the application's engine."""

from sqlalchemy import Engine, text

from app.database import session_scope


def test_connects_with_psycopg3_to_postgresql_18(db_engine: Engine) -> None:
    with db_engine.connect() as connection:
        version = connection.execute(text("SHOW server_version")).scalar_one()

    assert db_engine.dialect.driver == "psycopg"
    assert str(version).startswith("18.")


def test_session_scope_rolls_back_on_error(db_engine: Engine) -> None:
    """A failed unit of work leaves nothing behind (FR-ING-002, PRD 8.3)."""
    table = "p2t2_rollback_probe"
    with db_engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE {table} (id int)"))
    try:
        try:
            with session_scope() as session:
                session.execute(text(f"INSERT INTO {table} VALUES (1)"))
                raise RuntimeError("simulated failure")
        except RuntimeError:
            pass

        with db_engine.connect() as connection:
            rows = connection.execute(
                text(f"SELECT count(*) FROM {table}")
            ).scalar_one()
        assert rows == 0
    finally:
        with db_engine.begin() as connection:
            connection.execute(text(f"DROP TABLE {table}"))

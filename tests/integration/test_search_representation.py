"""The full-text search column on passages (P4-T2, FR-RET-001).

Configuration is in docs/design/retrieval.md. Each test runs in a transaction
that is rolled back.
"""

import hashlib
import itertools
import uuid

import pytest
from sqlalchemy import Connection, select, text
from sqlalchemy.exc import DBAPIError

from app.models import Passage
from app.models.passage import SEARCH_VECTOR_SQL

_n = itertools.count()


def add_passage(conn: Connection, body: str) -> uuid.UUID:
    n = next(_n)
    document_id = conn.execute(
        text(
            "INSERT INTO documents (sha256, size_bytes, storage_key) "
            "VALUES (:sha, 10, :key) RETURNING id"
        ),
        {"sha": hashlib.sha256(f"search-{n}".encode()).hexdigest(), "key": f"pdf/s{n}"},
    ).scalar_one()
    new_id: uuid.UUID = conn.execute(
        text(
            "INSERT INTO passages (document_id, ordinal, region, text) "
            "VALUES (:d, 0, 'body', :t) RETURNING id"
        ),
        {"d": document_id, "t": body},
    ).scalar_one()
    return new_id


def matches(conn: Connection, passage_id: uuid.UUID, query: str) -> bool:
    return bool(
        conn.execute(
            text(
                "SELECT search_vector @@ plainto_tsquery('english', :q) "
                "FROM passages WHERE id = :id"
            ),
            {"q": query, "id": passage_id},
        ).scalar_one()
    )


def lexemes(conn: Connection, passage_id: uuid.UUID) -> list[str]:
    return list(
        conn.execute(
            text(
                "SELECT tsvector_to_array(search_vector) FROM passages WHERE id = :id"
            ),
            {"id": passage_id},
        ).scalar_one()
    )


def test_new_passage_is_searchable_without_a_manual_step(conn: Connection) -> None:
    passage = add_passage(conn, "The experiments replicated earlier studies.")

    assert matches(conn, passage, "replication experiment")  # stems match
    assert not matches(conn, passage, "citation")


def test_stop_words_are_not_indexed(conn: Connection) -> None:
    assert "the" not in lexemes(conn, add_passage(conn, "The model and the data."))


def test_configuration_does_not_depend_on_the_session_default(conn: Connection) -> None:
    conn.execute(text("SET LOCAL default_text_search_config = 'simple'"))

    words = lexemes(conn, add_passage(conn, "The running experiments."))

    assert words == ["experi", "run"]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("--- %%% ()", []),
        ("β-catenin levels", ["catenin", "level", "β", "β-catenin"]),
        ("中文 😀", ["中文"]),
    ],
)
def test_unusual_text_is_stored_without_error(
    conn: Connection, body: str, expected: list[str]
) -> None:
    assert lexemes(conn, add_passage(conn, body)) == expected


def test_search_column_cannot_be_written(conn: Connection) -> None:
    """It is derived from the passage text, so it can never disagree with it."""
    document_id = conn.execute(
        text(
            "INSERT INTO documents (sha256, size_bytes, storage_key) "
            "VALUES (repeat('c', 64), 10, 'pdf/w') RETURNING id"
        )
    ).scalar_one()

    with pytest.raises(DBAPIError, match="non-DEFAULT value"):
        conn.execute(
            text(
                "INSERT INTO passages (document_id, ordinal, region, text, search_vector) "
                "VALUES (:d, 0, 'body', 'x', 'made up'::tsvector)"
            ),
            {"d": document_id},
        )


def test_search_uses_the_gin_index(conn: Connection) -> None:
    definition = conn.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE indexname = 'ix_passages_search_vector'"
        )
    ).scalar_one()
    assert "USING gin (search_vector)" in definition

    conn.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        conn.execute(
            text(
                "EXPLAIN SELECT id FROM passages "
                "WHERE search_vector @@ plainto_tsquery('english', 'experiment')"
            )
        ).scalars()
    )
    assert "ix_passages_search_vector" in plan


def test_loading_passages_does_not_load_the_search_column() -> None:
    """Ingestion and the structure view read passages and never need it."""
    assert "search_vector" not in str(select(Passage))


def test_model_and_database_agree_on_the_expression(conn: Connection) -> None:
    """`alembic check` does not compare generated-column expressions."""
    stored = conn.execute(
        text(
            "SELECT generation_expression FROM information_schema.columns "
            "WHERE table_name = 'passages' AND column_name = 'search_vector'"
        )
    ).scalar_one()

    assert stored == SEARCH_VECTOR_SQL

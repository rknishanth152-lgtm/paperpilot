"""Embedding stored passages, and the embeddings table (R2; FR-RET-005, AD-014)."""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_keyword_retrieval import add_document

from app.models import Paper, Passage, PassageEmbedding
from app.services.embeddings import (
    DocumentText,
    EmbeddingDimensionError,
    FakeEmbedder,
)
from app.services.llm import ModelError, ModelRateLimitError
from app.services.retrieval.embedding_job import (
    EmbeddingRun,
    count_missing_embeddings,
    embed_missing,
)

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "embed_passages.py"


def run(
    sessions: sessionmaker[Session], embedder: FakeEmbedder, batch_size: int = 2
) -> EmbeddingRun:
    return embed_missing(
        sessions,
        embedder,
        batch_size=batch_size,
        pause_seconds=0,
        sleep=lambda _: None,
    )


def stored(sessions: sessionmaker[Session]) -> list[PassageEmbedding]:
    with sessions() as session:
        return list(session.scalars(select(PassageEmbedding)))


def sent_texts(embedder: FakeEmbedder) -> list[str]:
    return [d.text for call in embedder.document_calls for d in call]


def test_every_passage_is_embedded_with_its_provenance(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "One.", "Two.", "Three.")
    embedder = FakeEmbedder(dimensions=3)

    result = run(sessions, embedder)

    assert result == EmbeddingRun(embedded=3, missing=0, stopped_by=None)
    rows = stored(sessions)
    assert len(rows) == 3
    for row in rows:
        assert row.model == "fake-embedding"
        assert row.dimensions == 3
        assert row.text_format == "fake-v1"
        assert len(row.embedding) == 3
    assert count_missing_embeddings(sessions, "fake-embedding") == 0


def test_the_vector_stored_is_the_vector_returned(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "One.")
    embedder = FakeEmbedder(dimensions=3)

    run(sessions, embedder)

    expected = FakeEmbedder(dimensions=3).embed_documents(embedder.document_calls[0])[0]
    assert stored(sessions)[0].embedding == pytest.approx(expected)


def test_the_paper_title_is_sent_and_a_missing_title_stays_missing(
    sessions: sessionmaker[Session],
) -> None:
    with sessions.begin() as session:
        named = Paper(metadata_source="grobid", title="Ice Studies")
        unnamed = Paper(metadata_source="grobid")
        session.add_all([named, unnamed])
        session.flush()
        ids = (named.id, unnamed.id)
    add_document(sessions, "One.", paper_id=ids[0])
    add_document(sessions, "Two.", paper_id=ids[1])
    embedder = FakeEmbedder(dimensions=3)

    run(sessions, embedder)

    sent = {d.text: d for d in embedder.document_calls[0]}
    assert sent["One."] == DocumentText(title="Ice Studies", text="One.")
    assert sent["Two."] == DocumentText(title=None, text="Two.")


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_a_document_that_is_not_parsed_is_not_embedded_or_counted(
    sessions: sessionmaker[Session], status: str
) -> None:
    add_document(sessions, "Hidden.", status=status)
    embedder = FakeEmbedder(dimensions=3)

    result = run(sessions, embedder)

    assert result == EmbeddingRun(embedded=0, missing=0, stopped_by=None)
    assert embedder.document_calls == []
    assert count_missing_embeddings(sessions, "fake-embedding") == 0


def test_a_second_run_sends_nothing(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "One.", "Two.")
    run(sessions, FakeEmbedder(dimensions=3))
    again = FakeEmbedder(dimensions=3)

    result = run(sessions, again)

    assert result == EmbeddingRun(embedded=0, missing=0, stopped_by=None)
    assert again.document_calls == []
    assert len(stored(sessions)) == 2


def test_a_rate_limit_keeps_earlier_batches_and_the_next_run_resumes(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "One.", "Two.", "Three.", "Four.", "Five.")
    limited = FakeEmbedder(dimensions=3, failures={2: ModelRateLimitError()})

    first = run(sessions, limited)

    assert first == EmbeddingRun(embedded=2, missing=3, stopped_by="model_rate_limited")
    assert len(stored(sessions)) == 2
    assert count_missing_embeddings(sessions, "fake-embedding") == 3

    resumed = FakeEmbedder(dimensions=3)
    second = run(sessions, resumed)

    assert second == EmbeddingRun(embedded=3, missing=0, stopped_by=None)
    assert len(stored(sessions)) == 5
    assert not set(sent_texts(resumed)) & set(sent_texts(limited))


def test_a_vector_of_the_wrong_size_stops_the_run_and_stores_nothing_of_it(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "One.", "Two.")

    result = run(
        sessions, FakeEmbedder(dimensions=3, failures={1: EmbeddingDimensionError()})
    )

    assert result == EmbeddingRun(
        embedded=0, missing=2, stopped_by="embedding_dimension_mismatch"
    )
    assert stored(sessions) == []


def test_batches_are_limited_and_pauses_fall_between_them(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "One.", "Two.", "Three.", "Four.", "Five.")
    embedder = FakeEmbedder(dimensions=3)
    pauses: list[float] = []

    embed_missing(
        sessions, embedder, batch_size=2, pause_seconds=7, sleep=pauses.append
    )

    assert [len(call) for call in embedder.document_calls] == [2, 2, 1]
    assert pauses == [7, 7]


def test_a_stored_size_that_differs_is_refused_before_anything_is_sent(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "One.")
    run(sessions, FakeEmbedder(dimensions=3))
    add_document(sessions, "Two.")
    bigger = FakeEmbedder(dimensions=4)

    with pytest.raises(EmbeddingDimensionError):
        run(sessions, bigger)

    assert bigger.document_calls == []


def test_another_models_embeddings_do_not_count(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "One.")
    run(sessions, FakeEmbedder(dimensions=3, model_name="old-model"))
    current = FakeEmbedder(dimensions=4, model_name="new-model")

    assert count_missing_embeddings(sessions, "new-model") == 1
    result = run(sessions, current)

    assert result.embedded == 1
    assert sorted(row.model for row in stored(sessions)) == ["new-model", "old-model"]


def test_passages_are_untouched_and_logs_carry_no_paper_text(
    sessions: sessionmaker[Session], caplog: pytest.LogCaptureFixture
) -> None:
    add_document(sessions, "A SECRET SENTENCE.")
    with sessions() as session:
        before = session.execute(select(Passage.id, Passage.text)).all()

    with caplog.at_level(logging.DEBUG):
        run(sessions, FakeEmbedder(dimensions=3))

    with sessions() as session:
        assert session.execute(select(Passage.id, Passage.text)).all() == before
    assert "SECRET" not in caplog.text


def test_the_command_starts_outside_pytest() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--check" in result.stdout


# --- The table ----------------------------------------------------------------


def passage_id(sessions: sessionmaker[Session]) -> Any:
    add_document(sessions, "One.")
    with sessions() as session:
        return session.scalars(select(Passage.id)).one()


def row(passage: Any, **values: Any) -> PassageEmbedding:
    fields: dict[str, Any] = {
        "passage_id": passage,
        "model": "m",
        "text_format": "f",
        "dimensions": 2,
        "embedding": [1.0, 0.0],
        **values,
    }
    return PassageEmbedding(**fields)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({"model": ""}, id="empty model"),
        pytest.param({"text_format": ""}, id="empty format"),
        pytest.param({"dimensions": 0, "embedding": [1.0]}, id="zero size"),
        pytest.param({"dimensions": 3}, id="size does not match the vector"),
    ],
)
def test_the_table_refuses_inconsistent_rows(
    sessions: sessionmaker[Session], values: dict[str, Any]
) -> None:
    passage = passage_id(sessions)

    with pytest.raises(IntegrityError), sessions.begin() as session:
        session.add(row(passage, **values))


def test_one_embedding_per_passage_and_model(sessions: sessionmaker[Session]) -> None:
    passage = passage_id(sessions)
    with sessions.begin() as session:
        session.add(row(passage))
        session.add(row(passage, model="other"))

    with pytest.raises(IntegrityError), sessions.begin() as session:
        session.add(row(passage))


def test_an_embedding_needs_a_real_passage(
    sessions: sessionmaker[Session], schema_engine: Engine
) -> None:
    passage = passage_id(sessions)
    with sessions.begin() as session:
        session.add(row(passage))

    with pytest.raises(DBAPIError), schema_engine.begin() as connection:
        connection.execute(text("DELETE FROM passages"))


def test_cosine_distance_works_on_stored_vectors(
    sessions: sessionmaker[Session], schema_engine: Engine
) -> None:
    passage = passage_id(sessions)
    with sessions.begin() as session:
        session.add(row(passage))

    with schema_engine.connect() as connection:
        distance = connection.execute(
            text("SELECT embedding <=> '[1,0]'::vector FROM passage_embeddings")
        ).scalar_one()

    assert distance == pytest.approx(0.0)


def test_a_model_error_is_reported_by_code(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "One.")

    result = run(
        sessions, FakeEmbedder(dimensions=3, failures={1: ModelErrorForTest()})
    )

    assert result.stopped_by == "test_failure"


class ModelErrorForTest(ModelError):
    code = "test_failure"
    message = "Failed."

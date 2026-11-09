"""The comparison's retrievers against the database (R4; FR-RET-007)."""

from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.evaluation.compare_retrieval import (
    ComparisonError,
    hybrid_retriever,
    semantic_retriever,
)
from tests.integration.test_keyword_retrieval import add_document

from app.services.embeddings import FakeEmbedder
from app.services.llm import ModelRateLimitError
from app.services.retrieval.embedding_job import embed_missing


def embed(sessions: sessionmaker[Session]) -> None:
    embed_missing(
        sessions,
        FakeEmbedder(dimensions=3),
        batch_size=10,
        pause_seconds=0,
        sleep=lambda _: None,
    )


def build_hybrid(
    sessions: sessionmaker[Session], embedder: FakeEmbedder | None = None
) -> Any:
    return hybrid_retriever(
        sessions,
        embedder or FakeEmbedder(dimensions=3),
        candidates=10,
        rrf_constant=60,
        max_query_chars=100,
    )


def build_semantic(sessions: sessionmaker[Session]) -> Any:
    return semantic_retriever(sessions, FakeEmbedder(dimensions=3), max_query_chars=100)


def test_the_retrievers_return_passages_in_scope(
    sessions: sessionmaker[Session],
) -> None:
    wanted = add_document(sessions, "Glaciers retreated.")
    add_document(sessions, "Glaciers elsewhere.")
    embed(sessions)

    for retrieve in (build_semantic(sessions), build_hybrid(sessions)):
        found = retrieve("glaciers", 5, [wanted])
        assert [p.text for p in found] == ["Glaciers retreated."]


@pytest.mark.parametrize("build", [build_semantic, build_hybrid])
def test_missing_embeddings_invalidate_the_comparison(
    sessions: sessionmaker[Session], build: Any
) -> None:
    document = add_document(sessions, "Glaciers retreated.")

    with pytest.raises(ComparisonError, match="missing"):
        build(sessions)("glaciers", 5, [document])


def test_a_semantic_failure_invalidates_the_hybrid_comparison(
    sessions: sessionmaker[Session],
) -> None:
    document = add_document(sessions, "Glaciers retreated.")
    embed(sessions)
    failing = FakeEmbedder(dimensions=3, failures={1: ModelRateLimitError()})

    with pytest.raises(ComparisonError, match="model_rate_limited"):
        build_hybrid(sessions, failing)("glaciers", 5, [document])

"""The retrieval method answering uses (R4; FR-RET-007, DR-006)."""

import json
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_keyword_retrieval import add_document
from tests.unit.test_answer_call import VALID, limits

from app.config import Settings
from app.services.answering.pipeline import Answering
from app.services.embeddings import FakeEmbedder
from app.services.llm import FakeModel, ModelRateLimitError
from app.services.retrieval.embedding_job import embed_missing
from app.services.retrieval.selection import (
    KEYWORD_METHOD,
    SEMANTIC_METHOD,
    KeywordRetriever,
    SemanticRetriever,
    build_retriever,
)

VECTORS: dict[str, list[float]] = {
    "the query": [1.0, 0.0],
    "Near passage.": [0.99, 0.14],
    "Far passage.": [0.0, 1.0],
}


def embedder(**values: Any) -> FakeEmbedder:
    return FakeEmbedder(**{"dimensions": 2, "vectors": VECTORS, **values})


def embed_stored(sessions: sessionmaker[Session]) -> None:
    embed_missing(
        sessions, embedder(), batch_size=10, pause_seconds=0, sleep=lambda _: None
    )


def retrieve(retriever: Any, question: str = "the query", **scope: Any) -> Any:
    return retriever(
        question,
        k=5,
        max_query_chars=100,
        document_ids=scope.get("document_ids"),
        paper_ids=scope.get("paper_ids"),
    )


def test_keyword_retrieval_names_itself(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "Glaciers retreated.")

    result = retrieve(KeywordRetriever(sessions), "glaciers")

    assert [p.text for p in result.passages] == ["Glaciers retreated."]
    assert result.method == KEYWORD_METHOD == "keyword_full_text"


def test_semantic_retrieval_names_itself(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "Far passage.", "Near passage.")
    embed_stored(sessions)

    result = retrieve(SemanticRetriever(sessions, embedder()))

    assert result.passages[0].text == "Near passage."
    assert result.method == SEMANTIC_METHOD == "semantic_cosine"


def test_a_paper_without_embeddings_uses_keyword_search_and_says_so(
    sessions: sessionmaker[Session],
) -> None:
    done = add_document(sessions, "Glaciers near.")
    embed_stored(sessions)
    new = add_document(sessions, "Glaciers retreated.")
    used = embedder()
    retriever = SemanticRetriever(sessions, used)

    result = retrieve(retriever, "glaciers", document_ids=[new])
    other = retrieve(retriever, "glaciers", document_ids=[done])

    assert [p.text for p in result.passages] == ["Glaciers retreated."]
    assert result.method == KEYWORD_METHOD
    assert other.method == SEMANTIC_METHOD


def test_a_partly_embedded_scope_uses_keyword_search_for_all_of_it(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers near.")
    embed_stored(sessions)
    add_document(sessions, "Glaciers retreated.")

    result = retrieve(SemanticRetriever(sessions, embedder()), "glaciers")

    assert {p.text for p in result.passages} == {
        "Glaciers near.",
        "Glaciers retreated.",
    }
    assert result.method == KEYWORD_METHOD


def test_a_provider_failure_is_an_explicit_error(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions)
    failing = embedder(failures={1: ModelRateLimitError()})

    with pytest.raises(ModelRateLimitError):
        retrieve(SemanticRetriever(sessions, failing))


def settings(**values: Any) -> Settings:
    fields: dict[str, Any] = {
        "postgres_password": "x",
        "llm_provider": "gemini",
        "llm_model": "m",
        "llm_api_key": "not-real",
        **values,
    }
    return Settings(_env_file=None, **fields)


def test_semantic_is_the_default(sessions: sessionmaker[Session]) -> None:
    assert isinstance(build_retriever(settings(), sessions), SemanticRetriever)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({"retrieval_method": "keyword"}, id="chosen"),
        pytest.param({"llm_provider": "anthropic"}, id="key is for another provider"),
    ],
)
def test_keyword_is_used_when_semantic_does_not_apply(
    sessions: sessionmaker[Session], values: dict[str, Any]
) -> None:
    assert isinstance(build_retriever(settings(**values), sessions), KeywordRetriever)


def test_an_unknown_method_is_refused() -> None:
    with pytest.raises(ValueError):
        settings(retrieval_method="other")


def test_answering_uses_the_retriever_and_reports_it(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Far passage.", "Near passage.")
    embed_stored(sessions)
    model = FakeModel([VALID])
    answering = Answering(
        sessions, model, limits(top_k=1), SemanticRetriever(sessions, embedder())
    )

    result = answering.answer("the query")

    sent = json.loads(model.requests[0].user)
    assert [p["text"] for p in sent["passages"]] == ["Near passage."]
    assert result.retrieval_method == SEMANTIC_METHOD


def test_answering_passes_the_scope_and_limits_to_the_retriever(
    sessions: sessionmaker[Session],
) -> None:
    wanted = add_document(sessions, "Far passage.")
    add_document(sessions, "Near passage.")
    embed_stored(sessions)
    model = FakeModel([VALID])

    Answering(sessions, model, limits(), SemanticRetriever(sessions, embedder())).ask(
        "the query", document_ids=[wanted]
    )

    assert [p["text"] for p in json.loads(model.requests[0].user)["passages"]] == [
        "Far passage."
    ]


def test_answering_without_a_retriever_uses_keyword_search(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated.")

    result = Answering(sessions, FakeModel([VALID]), limits()).answer("glaciers")

    assert result.retrieval_method == KEYWORD_METHOD


def test_no_evidence_still_reports_the_method(
    sessions: sessionmaker[Session],
) -> None:
    result = Answering(
        sessions, FakeModel([]), limits(), SemanticRetriever(sessions, embedder())
    ).answer("the query")

    assert result.evidence_sufficiency == "insufficient"
    assert result.retrieval_method == SEMANTIC_METHOD

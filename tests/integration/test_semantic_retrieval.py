"""Semantic and hybrid retrieval against pgvector (R3; FR-RET-005, FR-RET-006)."""

import logging
import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_keyword_retrieval import add_document, add_paper

from app.models import Passage, PassageEmbedding
from app.services.embeddings import EmbeddingDimensionError, FakeEmbedder
from app.services.llm import ModelRateLimitError
from app.services.retrieval.embedding_job import embed_missing
from app.services.retrieval.hybrid import search_hybrid
from app.services.retrieval.keyword import QueryTooLongError
from app.services.retrieval.semantic import search_semantic

QUERY = "the query"
NEAR, MIDDLE, FAR = [0.99, 0.14], [0.8, 0.6], [0.0, 1.0]
VECTORS: dict[str, list[float]] = {
    QUERY: [1.0, 0.0],
    "Near passage.": NEAR,
    "Middle passage.": MIDDLE,
    "Far passage.": FAR,
}


def embedder(**values: Any) -> FakeEmbedder:
    return FakeEmbedder(**{"dimensions": 2, "vectors": VECTORS, **values})


def embed_stored(sessions: sessionmaker[Session], **values: Any) -> None:
    embed_missing(
        sessions,
        embedder(**values),
        batch_size=50,
        pause_seconds=0,
        sleep=lambda _: None,
    )


def semantic(
    sessions: sessionmaker[Session],
    used: FakeEmbedder | None = None,
    question: str = QUERY,
    k: int = 5,
    **scope: Any,
) -> Any:
    return search_semantic(
        sessions,
        used or embedder(),
        question,
        k=k,
        max_query_chars=100,
        **scope,
    )


def hybrid(
    sessions: sessionmaker[Session],
    used: FakeEmbedder | None = None,
    question: str = QUERY,
    k: int = 5,
    candidates: int = 10,
    **scope: Any,
) -> Any:
    return search_hybrid(
        sessions,
        used or embedder(),
        question,
        k=k,
        candidates=candidates,
        rrf_constant=60,
        max_query_chars=100,
        **scope,
    )


def texts(passages: list[Any]) -> list[str]:
    return [p.text for p in passages]


# --- Semantic ------------------------------------------------------------------


def test_results_are_ordered_by_similarity_with_a_cosine_score(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Far passage.", "Near passage.", "Middle passage.")
    embed_stored(sessions)

    result = semantic(sessions)

    assert texts(result.passages) == [
        "Near passage.",
        "Middle passage.",
        "Far passage.",
    ]
    assert result.passages[1].score == pytest.approx(0.8)
    assert result.passages[2].score == pytest.approx(0.0)
    assert result.missing_embeddings == 0


def test_a_passage_sharing_no_word_with_the_question_is_found(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions)

    assert texts(semantic(sessions, question=QUERY).passages) == ["Near passage."]


def test_the_location_comes_from_the_database(sessions: sessionmaker[Session]) -> None:
    paper = add_paper(sessions)
    document = add_document(
        sessions,
        {
            "text": "Near passage.",
            "section_title": "Results",
            "page_start": 2,
            "page_end": 3,
        },
        paper_id=paper,
    )
    embed_stored(sessions)

    [found] = semantic(sessions).passages

    assert (found.document_id, found.paper_id) == (document, paper)
    assert (found.section, found.page_start, found.page_end) == ("Results", 2, 3)


def test_k_limits_the_results(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "Far passage.", "Near passage.", "Middle passage.")
    embed_stored(sessions)

    assert texts(semantic(sessions, k=2).passages) == [
        "Near passage.",
        "Middle passage.",
    ]


def test_k_must_be_positive(sessions: sessionmaker[Session]) -> None:
    with pytest.raises(ValueError):
        semantic(sessions, k=0)


def test_equal_scores_are_ordered_by_passage_id(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Same one.", "Same two.", "Same three.")
    same = {"Same one.": NEAR, "Same two.": NEAR, "Same three.": NEAR, QUERY: NEAR}
    embed_stored(sessions, vectors=same)

    ids = [p.passage_id for p in semantic(sessions, embedder(vectors=same)).passages]

    assert ids == sorted(ids)


def test_document_scope(sessions: sessionmaker[Session]) -> None:
    wanted = add_document(sessions, "Middle passage.")
    add_document(sessions, "Near passage.")
    embed_stored(sessions)

    result = semantic(sessions, document_ids=[wanted])

    assert texts(result.passages) == ["Middle passage."]


def test_paper_scope(sessions: sessionmaker[Session]) -> None:
    paper = add_paper(sessions)
    add_document(sessions, "Middle passage.", paper_id=paper)
    add_document(sessions, "Near passage.")
    embed_stored(sessions)

    assert texts(semantic(sessions, paper_ids=[paper]).passages) == ["Middle passage."]


def test_both_scopes_must_hold(sessions: sessionmaker[Session]) -> None:
    paper = add_paper(sessions)
    document = add_document(sessions, "Middle passage.", paper_id=paper)
    other = add_paper(sessions)
    add_document(sessions, "Near passage.", paper_id=other)
    embed_stored(sessions)

    result = semantic(sessions, document_ids=[document], paper_ids=[other])

    assert result.passages == []


@pytest.mark.parametrize(
    "scope",
    [
        pytest.param({"document_ids": []}, id="empty documents"),
        pytest.param({"paper_ids": []}, id="empty papers"),
        pytest.param({"document_ids": [uuid.uuid4()]}, id="unknown document"),
    ],
)
def test_a_scope_holding_nothing_finds_nothing_and_sends_nothing(
    sessions: sessionmaker[Session], scope: dict[str, Any]
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions)
    used = embedder()

    result = semantic(sessions, used, **scope)

    assert (result.passages, result.missing_embeddings) == ([], 0)
    assert used.query_calls == []


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_a_document_that_is_not_parsed_is_not_searched(
    sessions: sessionmaker[Session], status: str
) -> None:
    document = add_document(sessions, "Near passage.")
    embed_stored(sessions)
    hidden = add_document(sessions, "Middle passage.", status=status)
    used = embedder()

    result = semantic(sessions, used, document_ids=[document, hidden])

    assert texts(result.passages) == ["Near passage."]
    assert result.missing_embeddings == 0


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_a_stored_embedding_of_an_unparsed_document_is_not_returned(
    sessions: sessionmaker[Session], status: str
) -> None:
    hidden = add_document(sessions, "Near passage.", status=status)
    with sessions.begin() as session:
        passage = session.scalars(
            select(Passage.id).where(Passage.document_id == hidden)
        ).one()
        session.add(
            PassageEmbedding(
                passage_id=passage,
                model="fake-embedding",
                text_format="fake-v1",
                dimensions=2,
                embedding=NEAR,
            )
        )
    add_document(sessions, "Middle passage.")
    embed_stored(sessions)

    assert texts(semantic(sessions).passages) == ["Middle passage."]


def test_a_passage_with_two_models_is_returned_once(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions, model_name="old-model")
    embed_stored(sessions)

    assert texts(semantic(sessions).passages) == ["Near passage."]


def test_another_models_embeddings_are_not_used(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions, model_name="old-model")
    used = embedder()

    result = semantic(sessions, used)

    assert (result.passages, result.missing_embeddings) == ([], 1)
    assert used.query_calls == []


def test_missing_embeddings_are_reported_for_the_scope(
    sessions: sessionmaker[Session],
) -> None:
    done = add_document(sessions, "Near passage.")
    embed_stored(sessions)
    partly = add_document(sessions, "Middle passage.", "Far passage.")

    everything = semantic(sessions)
    only_done = semantic(sessions, document_ids=[done])
    only_new = semantic(sessions, document_ids=[partly])

    assert texts(everything.passages) == ["Near passage."]
    assert everything.missing_embeddings == 2
    assert only_done.missing_embeddings == 0
    assert (only_new.passages, only_new.missing_embeddings) == ([], 2)


def test_an_over_long_question_is_refused_before_anything_is_sent(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions)
    used = embedder()

    with pytest.raises(QueryTooLongError):
        semantic(sessions, used, question="x" * 101)

    assert used.query_calls == []


@pytest.mark.parametrize("question", ["", "    ", "\x00"])
def test_a_blank_question_finds_nothing_and_sends_nothing(
    sessions: sessionmaker[Session], question: str
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions)
    used = embedder()

    assert semantic(sessions, used, question=question).passages == []
    assert used.query_calls == []


def test_the_question_is_cleaned_before_it_is_sent(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions)
    used = embedder()

    semantic(sessions, used, question="a\x00b")

    assert used.query_calls == ["a b"]


def test_a_stored_size_that_differs_is_refused_before_anything_is_sent(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions)
    used = embedder(dimensions=3, vectors={})

    with pytest.raises(EmbeddingDimensionError):
        semantic(sessions, used)

    assert used.query_calls == []


def test_a_provider_failure_is_raised_not_hidden(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions)

    with pytest.raises(ModelRateLimitError):
        semantic(sessions, embedder(failures={1: ModelRateLimitError()}))


def test_logs_carry_no_question_or_passage_text(
    sessions: sessionmaker[Session], caplog: pytest.LogCaptureFixture
) -> None:
    add_document(sessions, "Near SECRET passage.")
    embed_stored(sessions)

    with caplog.at_level(logging.DEBUG):
        semantic(sessions, question="a HIDDEN question")
        hybrid(sessions, question="a HIDDEN question")

    assert "SECRET" not in caplog.text
    assert "HIDDEN" not in caplog.text


# --- Hybrid --------------------------------------------------------------------


def test_both_methods_contribute(sessions: sessionmaker[Session]) -> None:
    add_document(sessions, "Near passage.", "Far glacier.")
    vectors = {**VECTORS, "Far glacier.": FAR, "glacier": NEAR}
    embed_stored(sessions, vectors=vectors)

    result = hybrid(sessions, embedder(vectors=vectors), question="glacier", k=2)

    assert set(texts(result.passages)) == {"Near passage.", "Far glacier."}
    assert result.methods == ("keyword", "semantic")
    assert result.semantic_failure is None


def test_a_passage_found_by_both_methods_ranks_first(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.", "Middle glacier.", "Far passage.")
    vectors = {**VECTORS, "Middle glacier.": MIDDLE, "glacier": [1.0, 0.0]}
    embed_stored(sessions, vectors=vectors)

    result = hybrid(sessions, embedder(vectors=vectors), question="glacier")

    assert result.passages[0].text == "Middle glacier."


def test_a_semantic_failure_leaves_keyword_results_and_says_so(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated.")
    embed_stored(sessions)

    result = hybrid(
        sessions,
        embedder(failures={1: ModelRateLimitError()}),
        question="glaciers",
    )

    assert texts(result.passages) == ["Glaciers retreated."]
    assert result.methods == ("keyword",)
    assert result.semantic_failure == "model_rate_limited"


def test_no_embeddings_leaves_keyword_results_and_reports_them_missing(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated.")

    result = hybrid(sessions, question="glaciers")

    assert texts(result.passages) == ["Glaciers retreated."]
    assert result.methods == ("keyword",)
    assert result.semantic_failure is None
    assert result.missing_embeddings == 1


def test_no_keyword_match_leaves_semantic_results(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.")
    embed_stored(sessions)

    result = hybrid(sessions, question=QUERY)

    assert texts(result.passages) == ["Near passage."]
    assert result.methods == ("semantic",)


def test_nothing_from_either_method_is_an_empty_result(
    sessions: sessionmaker[Session],
) -> None:
    result = hybrid(sessions)

    assert (result.passages, result.methods) == ([], ())


def test_a_method_with_nothing_in_the_final_list_is_not_named(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.", "Far glacier.")
    vectors = {**VECTORS, "Far glacier.": FAR, "glacier": NEAR}
    embed_stored(sessions, vectors=vectors)

    # Each method has one candidate, tied in rank; the lower passage id stays.
    result = hybrid(
        sessions, embedder(vectors=vectors), question="glacier", k=1, candidates=1
    )

    assert texts(result.passages) == ["Near passage."]
    assert result.methods == ("semantic",)


def test_scope_applies_to_both_methods(sessions: sessionmaker[Session]) -> None:
    wanted = add_document(sessions, "Far glacier.")
    add_document(sessions, "Near glacier.")
    vectors = {**VECTORS, "Far glacier.": FAR, "Near glacier.": NEAR, "glacier": NEAR}
    embed_stored(sessions, vectors=vectors)

    result = hybrid(
        sessions,
        embedder(vectors=vectors),
        question="glacier",
        document_ids=[wanted],
    )

    assert texts(result.passages) == ["Far glacier."]


def test_candidates_limit_each_method_and_k_limits_the_result(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Near passage.", "Middle passage.", "Far passage.")
    embed_stored(sessions)

    assert len(hybrid(sessions, k=2, candidates=3).passages) == 2
    assert texts(hybrid(sessions, k=2, candidates=2).passages) == [
        "Near passage.",
        "Middle passage.",
    ]


def test_keyword_search_also_supplies_all_its_candidates(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers one.", "Glaciers two.")

    result = hybrid(sessions, question="glaciers", k=2, candidates=2)

    assert len(result.passages) == 2
    assert result.methods == ("keyword",)


def test_candidates_cannot_be_fewer_than_k(sessions: sessionmaker[Session]) -> None:
    with pytest.raises(ValueError):
        hybrid(sessions, k=5, candidates=4)


def test_an_over_long_question_is_refused(sessions: sessionmaker[Session]) -> None:
    used = embedder()

    with pytest.raises(QueryTooLongError):
        hybrid(sessions, used, question="x" * 101)

    assert used.query_calls == []

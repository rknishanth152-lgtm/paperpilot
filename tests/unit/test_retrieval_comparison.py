"""Comparing retrieval methods, with no model or database (R4; FR-RET-007)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from tests.evaluation.code_state import CodeState
from tests.evaluation.compare_retrieval import (
    CachedQueryEmbedder,
    compare_methods,
    comparison_record,
    recommended_method,
    write_comparison,
)
from tests.unit.test_retrieval_harness import (
    ANSWER,
    DOCUMENTS,
    OTHER,
    P1,
    PASSAGES,
    QUOTE,
    evaluation_set,
    question,
    retriever,
    unanswerable,
)

from app.services.embeddings import FakeEmbedder

RUN_AT = datetime(2026, 11, 9, 8, 30, 5, tzinfo=UTC)
STATE = CodeState(revision="abcdef1234567", clean=True)
EVALUATION = evaluation_set(question("q01", P1, QUOTE), unanswerable("q02"))


def summary(hits_all: int, hits_paper: int | None = None) -> dict[str, int]:
    return {
        "hits_all_papers": hits_all,
        "hits_question_paper": hits_all if hits_paper is None else hits_paper,
    }


@pytest.mark.parametrize(
    ("keyword", "semantic", "hybrid", "expected"),
    [
        pytest.param(summary(8), summary(8), summary(8), "keyword", id="no change"),
        pytest.param(summary(8), summary(9), summary(9), "keyword", id="gain of one"),
        pytest.param(summary(8), summary(10), summary(8), "semantic", id="semantic"),
        pytest.param(summary(8), summary(8), summary(10), "hybrid", id="hybrid"),
        pytest.param(summary(8), summary(12), summary(10), "semantic", id="best wins"),
        pytest.param(
            summary(8), summary(10), summary(10), "hybrid", id="tie is hybrid"
        ),
        pytest.param(
            summary(8, 9),
            summary(11, 8),
            summary(10, 9),
            "hybrid",
            id="worse within the paper is excluded",
        ),
        pytest.param(
            summary(8, 9), summary(10, 8), summary(10, 8), "keyword", id="both excluded"
        ),
        pytest.param(
            summary(8, 9),
            summary(10, 10),
            summary(10, 12),
            "hybrid",
            id="tie is split by the paper figure",
        ),
        pytest.param(
            summary(8, 9),
            summary(10, 12),
            summary(10, 10),
            "semantic",
            id="the paper figure comes before preferring hybrid",
        ),
    ],
)
def test_the_default_changes_only_by_the_rule_set_in_advance(
    keyword: dict[str, int],
    semantic: dict[str, int],
    hybrid: dict[str, int],
    expected: str,
) -> None:
    summaries = {"keyword": keyword, "semantic": semantic, "hybrid": hybrid}

    assert recommended_method(summaries) == expected


def test_a_query_is_embedded_once_with_a_pause_between_new_queries() -> None:
    inner = FakeEmbedder(dimensions=3)
    pauses: list[float] = []
    cached = CachedQueryEmbedder(inner, pause=4.0, sleep=pauses.append)

    first = cached.embed_query("one")
    again = cached.embed_query("one")
    cached.embed_query("two")

    assert first == again
    assert inner.query_calls == ["one", "two"]
    assert pauses == [4.0]


def test_the_cached_embedder_describes_the_real_one() -> None:
    inner = FakeEmbedder(dimensions=3, model_name="m")
    cached = CachedQueryEmbedder(inner, pause=0)

    assert (cached.model_name, cached.dimensions, cached.text_format) == (
        "m",
        3,
        inner.text_format,
    )
    assert cached.embed_documents([]) == []


def compared() -> dict[str, Any]:
    return compare_methods(
        EVALUATION,
        DOCUMENTS,
        PASSAGES,
        {
            "keyword": retriever(OTHER.passage_id),
            "hybrid": retriever(OTHER.passage_id, ANSWER.passage_id),
        },
    )


def test_each_method_is_scored_on_the_same_questions() -> None:
    result = compared()

    assert result["methods"]["keyword"]["summary"]["hits_all_papers"] == 0
    assert result["methods"]["hybrid"]["summary"]["hits_all_papers"] == 1


def test_the_ranks_are_listed_per_question_for_answerable_questions_only() -> None:
    assert compared()["by_question"] == [
        {
            "id": "q01",
            "rank_all_papers": {"keyword": None, "hybrid": 2},
            "rank_question_paper": {"keyword": None, "hybrid": 2},
        }
    ]


def record() -> dict[str, Any]:
    return comparison_record(
        {
            "methods": {"keyword": {"summary": summary(8)}},
            "by_question": [],
        },
        evaluation=EVALUATION,
        evaluation_sha256="e" * 64,
        run_at=RUN_AT,
        state=STATE,
        configuration={"k": 5},
    )


def test_a_saved_comparison_says_how_it_was_made() -> None:
    saved = record()

    assert saved["kind"] == "retrieval comparison"
    assert saved["code_revision"] == STATE.revision
    assert saved["working_tree_clean"] is True
    assert saved["run_at"] == RUN_AT.isoformat()
    assert saved["configuration"] == {"k": 5}
    assert saved["evaluation_set"]["sha256"] == "e" * 64
    assert saved["limits"] == "small"
    assert saved["recommended_default"] == "keyword"


def test_a_comparison_is_written_to_a_new_dated_file(tmp_path: Path) -> None:
    saved = record()

    path = write_comparison(saved, tmp_path)

    assert path.name == "retrieval-comparison-20261109T083005Z-abcdef1.json"
    assert json.loads(path.read_text(encoding="utf-8")) == saved
    with pytest.raises(FileExistsError):
        write_comparison(saved, tmp_path)

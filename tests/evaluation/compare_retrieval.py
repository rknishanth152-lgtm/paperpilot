"""Compare keyword, semantic and hybrid retrieval on the same set (R4; FR-RET-007).

From the repository folder, with PostgreSQL running and passages embedded:

    uv run python -m tests.evaluation.compare_retrieval

A manual real-model run: each question is sent once to the embedding provider.
No model answers anything and no passage text is sent. Saves one new dated file.
A run with missing embeddings or a semantic failure is refused, because it would
not be a fair comparison.

The rule for changing the default is `recommended_method`, fixed before the first
run (docs/experiments/retrieval-comparison.md).
"""

import argparse
import hashlib
import json
import sys
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy.orm import Session, sessionmaker
from tests.evaluation.code_state import CodeState, code_state
from tests.evaluation.dataset import (
    EVALUATION_SET,
    EvaluationSet,
    load_evaluation_set,
)
from tests.evaluation.retrieval_harness import (
    K,
    Retrieved,
    Retriever,
    StoredPassage,
    evaluate,
    keyword_retriever,
    load_corpus,
    require_reviewed,
)

from app.config import get_settings
from app.database import get_sessionmaker
from app.services.embeddings import DocumentText, Embedder
from app.services.llm import ModelError
from app.services.llm_factory import build_embedder
from app.services.retrieval.hybrid import search_hybrid
from app.services.retrieval.semantic import search_semantic

RESULTS = REPO_ROOT / "benchmarks" / "results"
# With 16 questions, one question either way is not a meaningful difference.
MINIMUM_GAIN = 2
QUERY_PAUSE = 3.0


class ComparisonError(Exception):
    """The run cannot be a fair comparison."""


class CachedQueryEmbedder:
    """Embeds each question once, so every method and scope sees the same vector."""

    def __init__(
        self,
        embedder: Embedder,
        *,
        pause: float,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._embedder = embedder
        self._pause = pause
        self._sleep = sleep
        self._vectors: dict[str, list[float]] = {}

    @property
    def model_name(self) -> str:
        return self._embedder.model_name

    @property
    def dimensions(self) -> int:
        return self._embedder.dimensions

    @property
    def text_format(self) -> str:
        return self._embedder.text_format

    def embed_documents(self, documents: Sequence[DocumentText]) -> list[list[float]]:
        return self._embedder.embed_documents(documents)

    def embed_query(self, query: str) -> list[float]:
        if query not in self._vectors:
            if self._vectors:
                self._sleep(self._pause)
            self._vectors[query] = self._embedder.embed_query(query)
        return self._vectors[query]


def semantic_retriever(
    sessions: sessionmaker[Session], embedder: Embedder, *, max_query_chars: int
) -> Retriever:
    def retrieve(
        question: str, k: int, document_ids: Sequence[uuid.UUID]
    ) -> Sequence[Retrieved]:
        result = search_semantic(
            sessions,
            embedder,
            question,
            k=k,
            max_query_chars=max_query_chars,
            document_ids=document_ids,
        )
        if result.missing_embeddings:
            raise ComparisonError(f"{result.missing_embeddings} embeddings missing")
        return result.passages

    return retrieve


def hybrid_retriever(
    sessions: sessionmaker[Session],
    embedder: Embedder,
    *,
    candidates: int,
    rrf_constant: int,
    max_query_chars: int,
) -> Retriever:
    def retrieve(
        question: str, k: int, document_ids: Sequence[uuid.UUID]
    ) -> Sequence[Retrieved]:
        result = search_hybrid(
            sessions,
            embedder,
            question,
            k=k,
            candidates=candidates,
            rrf_constant=rrf_constant,
            max_query_chars=max_query_chars,
            document_ids=document_ids,
        )
        if result.semantic_failure:
            raise ComparisonError(f"semantic failed: {result.semantic_failure}")
        if result.missing_embeddings:
            raise ComparisonError(f"{result.missing_embeddings} embeddings missing")
        return result.passages

    return retrieve


def recommended_method(summaries: Mapping[str, Mapping[str, Any]]) -> str:
    """The default the recorded results justify, by the rule set in advance.

    A method qualifies if it finds at least `MINIMUM_GAIN` more expected passages
    than keyword across all papers, and no fewer within the question's paper.
    Of those, the most across all papers wins, then the most within the paper,
    then hybrid, which still answers from keyword search if embeddings fail.
    """
    base = summaries["keyword"]
    qualifying = [
        name
        for name in ("semantic", "hybrid")
        if summaries[name]["hits_all_papers"] >= base["hits_all_papers"] + MINIMUM_GAIN
        and summaries[name]["hits_question_paper"] >= base["hits_question_paper"]
    ]
    if not qualifying:
        return "keyword"
    return max(
        qualifying,
        key=lambda name: (
            summaries[name]["hits_all_papers"],
            summaries[name]["hits_question_paper"],
            name == "hybrid",
        ),
    )


def compare_methods(
    evaluation: EvaluationSet,
    documents: Mapping[str, uuid.UUID],
    passages: Mapping[str, Sequence[StoredPassage]],
    retrievers: Mapping[str, Retriever],
) -> dict[str, Any]:
    """Each method's result, and each answerable question's rank per method."""
    methods = {
        name: evaluate(evaluation, documents, passages, retrieve)
        for name, retrieve in retrievers.items()
    }

    def ranks(question_id: str, key: str) -> dict[str, int | None]:
        return {
            name: next(
                row[key] for row in result["questions"] if row["id"] == question_id
            )
            for name, result in methods.items()
        }

    return {
        "methods": methods,
        "by_question": [
            {
                "id": question.id,
                "rank_all_papers": ranks(question.id, "rank_all_papers"),
                "rank_question_paper": ranks(question.id, "rank_question_paper"),
            }
            for question in evaluation.questions
            if question.answerable
        ],
    }


def comparison_record(
    comparison: Mapping[str, Any],
    *,
    evaluation: EvaluationSet,
    evaluation_sha256: str,
    run_at: datetime,
    state: CodeState,
    configuration: Mapping[str, Any],
) -> dict[str, Any]:
    summaries = {
        name: result["summary"] for name, result in comparison["methods"].items()
    }
    recommended = (
        recommended_method(summaries)
        if {"semantic", "hybrid"} <= set(summaries)
        else "keyword"
    )
    return {
        "kind": "retrieval comparison",
        "run_at": run_at.isoformat(),
        "code_revision": state.revision,
        "working_tree_clean": state.clean,
        "configuration": dict(configuration),
        "evaluation_set": {
            "version": evaluation.version,
            "sha256": evaluation_sha256,
            "status": evaluation.status,
            "questions": len(evaluation.questions),
        },
        "limits": evaluation.limits,
        "recommended_default": recommended,
        **comparison,
    }


def write_comparison(record: Mapping[str, Any], directory: Path) -> Path:
    """Save to a new dated file. An existing result is never overwritten."""
    stamp = datetime.fromisoformat(record["run_at"]).strftime("%Y%m%dT%H%M%SZ")
    name = f"retrieval-comparison-{stamp}-{record['code_revision'][:7]}.json"
    path = directory / name
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pause", type=float, default=QUERY_PAUSE)
    options = parser.parse_args()

    evaluation = load_evaluation_set()
    require_reviewed(evaluation)
    settings = get_settings()
    sessions = get_sessionmaker()
    state = code_state()
    embedder = CachedQueryEmbedder(build_embedder(settings), pause=options.pause)
    limit = settings.max_query_chars
    documents, passages = load_corpus(sessions, evaluation)
    try:
        comparison = compare_methods(
            evaluation,
            documents,
            passages,
            {
                "keyword": keyword_retriever(sessions, max_query_chars=limit),
                "semantic": semantic_retriever(
                    sessions, embedder, max_query_chars=limit
                ),
                "hybrid": hybrid_retriever(
                    sessions,
                    embedder,
                    candidates=settings.hybrid_candidates,
                    rrf_constant=settings.hybrid_rrf_constant,
                    max_query_chars=limit,
                ),
            },
        )
    except (ModelError, ComparisonError) as error:
        print(f"Comparison stopped: {getattr(error, 'code', error)}", file=sys.stderr)
        return 1
    record = comparison_record(
        comparison,
        evaluation=evaluation,
        evaluation_sha256=hashlib.sha256(EVALUATION_SET.read_bytes()).hexdigest(),
        run_at=datetime.now(UTC),
        state=state,
        configuration={
            "k": K,
            "embedding_model": settings.embedding_model,
            "embedding_dimensions": settings.embedding_dimensions,
            "hybrid_candidates": settings.hybrid_candidates,
            "hybrid_rrf_constant": settings.hybrid_rrf_constant,
            "minimum_gain": MINIMUM_GAIN,
        },
    )
    path = write_comparison(record, RESULTS)
    for name, result in record["methods"].items():
        summary = result["summary"]
        print(
            f"{name}: {summary['hits_all_papers']}/{summary['evaluated']} all papers, "
            f"{summary['hits_question_paper']}/{summary['evaluated']} within the paper"
        )
    print(f"Recommended default: {record['recommended_default']}")
    print(f"Saved {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

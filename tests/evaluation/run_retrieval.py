"""Run the retrieval evaluation and save a dated result (P4-T6, FR-EVL-002).

From the repository folder, with PostgreSQL running and the corpus ingested:

    uv run python -m tests.evaluation.run_retrieval

Uses the database from `.env`. Reads only; writes one new file under
benchmarks/results/. Refuses a set that has not been reviewed.
"""

import hashlib
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from tests.evaluation.dataset import (
    EVALUATION_SET,
    load_evaluation_set,
)
from tests.evaluation.retrieval_harness import (
    K,
    evaluate,
    keyword_retriever,
    load_corpus,
    require_reviewed,
    result_record,
    write_result,
)

from app.config import get_settings
from app.database import get_sessionmaker
from app.models.passage import SEARCH_CONFIG, SEARCH_VECTOR_SQL

RESULTS = REPO_ROOT / "benchmarks" / "results"


def _git(*arguments: str) -> str:
    done = subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def main() -> None:
    evaluation = load_evaluation_set()
    require_reviewed(evaluation)
    settings = get_settings()
    sessions = get_sessionmaker()

    documents, passages = load_corpus(sessions, evaluation)
    result = evaluate(
        evaluation,
        documents,
        passages,
        keyword_retriever(sessions, max_query_chars=settings.max_query_chars),
    )
    record = result_record(
        result,
        evaluation=evaluation,
        evaluation_sha256=hashlib.sha256(EVALUATION_SET.read_bytes()).hexdigest(),
        run_at=datetime.now(UTC),
        code_revision=_git("rev-parse", "HEAD"),
        working_tree_clean=_git("status", "--porcelain") == "",
        configuration={
            "k": K,
            "retriever": "keyword",
            "search_config": SEARCH_CONFIG,
            "search_vector": SEARCH_VECTOR_SQL,
            "query": "plainto_tsquery with ANDs changed to ORs",
            "ranking": "ts_rank, normalisation 0, ties by passage id",
            "max_query_chars": settings.max_query_chars,
        },
    )
    path = write_result(record, RESULTS)

    summary = record["summary"]
    print(f"Saved {path.relative_to(REPO_ROOT)}")
    print(
        f"Recall@{summary['k']} across all papers: "
        f"{summary['hits_all_papers']}/{summary['evaluated']}"
    )
    print(
        f"Recall@{summary['k']} within the question's paper: "
        f"{summary['hits_question_paper']}/{summary['evaluated']}"
    )
    print(
        f"Unmatched: {summary['unmatched_questions']} questions, "
        f"{summary['unmatched_quotes']} quotes. Small set: {record['limits']}"
    )


if __name__ == "__main__":
    main()

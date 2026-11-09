"""Run the retrieval evaluation and save a dated result (P4-T6, FR-EVL-002).

From the repository folder, with PostgreSQL running and the corpus ingested:

    uv run python -m tests.evaluation.run_retrieval

Uses the database from `.env`. Reads only; writes one new file under
benchmarks/results/. Refuses a set that has not been reviewed.
"""

import argparse
import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

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
    evaluate,
    keyword_retriever,
    load_corpus,
    require_reviewed,
    result_record,
    write_result,
)

from app.config import Settings, get_settings
from app.database import get_sessionmaker
from app.models.passage import SEARCH_CONFIG, SEARCH_VECTOR_SQL

RESULTS = REPO_ROOT / "benchmarks" / "results"


def run_retrieval_evaluation(
    evaluation: EvaluationSet,
    settings: Settings,
    sessions: sessionmaker[Session],
    state: CodeState,
) -> Path:
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
        code_revision=state.revision,
        working_tree_clean=state.clean,
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
    print(f"Saved {path.name}")
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
    return path


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    evaluation = load_evaluation_set()
    require_reviewed(evaluation)
    run_retrieval_evaluation(
        evaluation, get_settings(), get_sessionmaker(), code_state()
    )


if __name__ == "__main__":
    main()

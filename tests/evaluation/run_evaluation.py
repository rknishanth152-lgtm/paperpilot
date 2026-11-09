"""Run the whole evaluation with one command (P6-T1; FR-EVL-002, FR-EVL-003).

Runs retrieval, then answers, on the same code, and saves a new dated file for
each in benchmarks/results/. From the repository folder, with PostgreSQL running
and the corpus ingested:

    uv run python -m tests.evaluation.run_evaluation --pause 30

The answer step is a manual real-model run: it sends the questions and retrieved
passages to the provider named in `.env`. Exits with 1 if the provider stops it.
"""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from tests.evaluation.code_state import CodeState, code_state
from tests.evaluation.dataset import load_evaluation_set
from tests.evaluation.retrieval_harness import require_reviewed
from tests.evaluation.run_answers import (
    DEFAULT_PAUSE,
    AnswerRun,
    run_answer_evaluation,
)
from tests.evaluation.run_retrieval import run_retrieval_evaluation

from app.config import get_settings
from app.database import get_sessionmaker


def run_all(
    state: CodeState,
    retrieval: Callable[[CodeState], Path],
    answers: Callable[[CodeState], AnswerRun],
) -> int:
    """Retrieval first: it needs no model, and its result stands on its own."""
    retrieval(state)
    run = answers(state)
    if run.stopped is not None:
        print(f"Answer evaluation stopped early: {run.stopped}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=None, help="default: LLM_MODEL from .env")
    parser.add_argument("--answer-limit", type=int, default=None)
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE)
    options = parser.parse_args()

    evaluation = load_evaluation_set()
    require_reviewed(evaluation)
    settings = get_settings()
    if options.model is not None:
        settings = settings.model_copy(update={"llm_model": options.model})
    sessions = get_sessionmaker()

    def retrieval(state: CodeState) -> Path:
        return run_retrieval_evaluation(evaluation, settings, sessions, state)

    def answers(state: CodeState) -> AnswerRun:
        return run_answer_evaluation(
            evaluation,
            settings,
            sessions,
            state,
            limit=options.answer_limit,
            pause=options.pause,
        )

    return run_all(code_state(), retrieval, answers)


if __name__ == "__main__":
    raise SystemExit(main())

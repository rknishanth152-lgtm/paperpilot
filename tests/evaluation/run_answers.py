"""A manual real-model run of the answering chain (P5-T12; AC-VS-06, AC-VS-07).

Sends the evaluation questions and the retrieved passages to the configured
provider. Not part of any test run. From the repository folder:

    uv run python -m tests.evaluation.run_answers --model gemini-3.8-flash

Saves a new file in benchmarks/results/, labelled as a manual run. Stops early
if the provider reports a rate limit, keeping what it has. The key is never
printed or saved.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from tests.evaluation.dataset import EVALUATION_SET, Question, load_evaluation_set
from tests.evaluation.retrieval_harness import (
    StoredPassage,
    expected_passages,
    load_corpus,
    require_reviewed,
)

from app.config import get_settings
from app.database import get_sessionmaker
from app.schemas.answer import MalformedAnswerError
from app.schemas.answer_response import AnswerResponse
from app.services.answering.pipeline import Answering, AnswerLimits
from app.services.answering.prompt import PROMPT_VERSION
from app.services.llm import LanguageModel, ModelError, ModelRequest, ModelResponse
from app.services.llm_factory import build_language_model

RESULTS = REPO_ROOT / "benchmarks" / "results"
# Standard paid prices, US$ per million tokens (input, output), read 2026-11-09.
# The free tier costs nothing; this is what the same usage would cost if paid.
PAID_PRICE = {
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-3.5-flash-lite": (0.30, 2.50),
}
Answer = Callable[[str, list[uuid.UUID]], AnswerResponse]


@dataclass
class Call:
    seconds: float
    input_tokens: int
    output_tokens: int


class TrackingModel:
    """Passes calls through and records time and tokens for each one."""

    def __init__(self, model: LanguageModel) -> None:
        self._model = model
        self.calls: list[Call] = []

    @property
    def model_name(self) -> str:
        return self._model.model_name

    def generate(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        response = self._model.generate(request)
        self.calls.append(
            Call(
                seconds=time.perf_counter() - started,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        )
        return response


def run_question(
    answer: Answer,
    tracker: TrackingModel,
    question: Question,
    document_ids: list[uuid.UUID],
    passages: dict[str, list[StoredPassage]],
) -> dict[str, Any]:
    """One question's full record. A model failure is recorded, not raised."""
    tracker.calls.clear()
    expected, _ = expected_passages(question, passages)
    row: dict[str, Any] = {
        "id": question.id,
        "answerable": question.answerable,
        "question": question.question,
        "error": None,
    }
    started = time.perf_counter()
    try:
        result = answer(question.question, document_ids)
    except (ModelError, MalformedAnswerError) as error:
        row["error"] = error.code
        result = None
    row.update(
        seconds=round(time.perf_counter() - started, 3),
        model_calls=len(tracker.calls),
        model_seconds=round(sum(call.seconds for call in tracker.calls), 3),
        input_tokens=sum(call.input_tokens for call in tracker.calls),
        output_tokens=sum(call.output_tokens for call in tracker.calls),
    )
    if result is None:
        return row
    cited = {e.passage_id for e in result.evidence}
    row.update(
        evidence_sufficiency=result.evidence_sufficiency,
        validation_status=result.validation_status,
        limitations=result.limitations,
        statements=[s.model_dump(mode="json") for s in result.statements],
        retrieved_passage_ids=[str(i) for i in result.retrieved_passage_ids],
        evidence_passage_ids=[str(i) for i in cited],
        expected_retrieved=bool(set(expected) & set(result.retrieved_passage_ids)),
        expected_cited=bool(set(expected) & cited),
        model=result.model,
        prompt_version=result.prompt_version,
    )
    return row


def summarize(rows: Sequence[dict[str, Any]], model: str) -> dict[str, Any]:
    answerable = [row for row in rows if row["answerable"]]
    unanswerable = [row for row in rows if not row["answerable"]]
    called = [row for row in rows if row["model_calls"]]
    tokens_in = sum(row["input_tokens"] for row in rows)
    tokens_out = sum(row["output_tokens"] for row in rows)
    price = PAID_PRICE.get(model)

    def count(items: Sequence[dict[str, Any]], key: str, value: object) -> int:
        return sum(row.get(key) == value for row in items)

    def errors(items: Sequence[dict[str, Any]]) -> int:
        return sum(row["error"] is not None for row in items)

    def stated(items: Sequence[dict[str, Any]]) -> int:
        return sum(bool(row.get("statements")) for row in items)

    return {
        "questions_run": len(rows),
        "answerable": {
            "total": len(answerable),
            "errors": errors(answerable),
            "validated_with_statements": sum(
                row.get("validation_status") == "validated"
                and bool(row.get("statements"))
                for row in answerable
            ),
            "failed_validation": count(answerable, "validation_status", "failed"),
            "said_insufficient": count(
                answerable, "evidence_sufficiency", "insufficient"
            ),
            "expected_passage_retrieved": count(answerable, "expected_retrieved", True),
            "expected_passage_cited": count(answerable, "expected_cited", True),
        },
        "unanswerable": {
            "total": len(unanswerable),
            "errors": errors(unanswerable),
            "said_insufficient": count(
                unanswerable, "evidence_sufficiency", "insufficient"
            ),
            "gave_statements": stated(unanswerable),
            "failed_validation": count(unanswerable, "validation_status", "failed"),
        },
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "mean_model_seconds": (
            round(sum(row["model_seconds"] for row in called) / len(called), 2)
            if called
            else None
        ),
        "paid_equivalent_usd_per_answer": (
            round((tokens_in * price[0] + tokens_out * price[1]) / 1e6 / len(called), 5)
            if price and called
            else None
        ),
    }


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--pause", type=float, default=7.0)
    parser.add_argument("--no-save", action="store_true")
    options = parser.parse_args()

    evaluation = load_evaluation_set()
    require_reviewed(evaluation)
    settings = get_settings().model_copy(update={"llm_model": options.model})
    sessions = get_sessionmaker()
    documents, passages = load_corpus(sessions, evaluation)
    tracker = TrackingModel(build_language_model(settings))
    answering = Answering(sessions, tracker, AnswerLimits.from_settings(settings))

    def answer(question: str, document_ids: list[uuid.UUID]) -> AnswerResponse:
        return answering.answer(question, document_ids=document_ids)

    questions = evaluation.questions[: options.limit]
    rows: list[dict[str, Any]] = []
    stopped: str | None = None
    for index, question in enumerate(questions):
        if index:
            time.sleep(options.pause)
        scope = [documents[p] for p in question.papers] or list(documents.values())
        row = run_question(answer, tracker, question, scope, passages)
        rows.append(row)
        outcome = row["error"] or (
            f"{row['evidence_sufficiency']}/{row['validation_status']}"
            f" cited_expected={row['expected_cited']}"
        )
        print(f"{row['id']} {outcome} ({row['model_seconds']}s)", flush=True)
        if row["error"] in ("model_rate_limited", "model_authentication_failed"):
            stopped = row["error"]
            break

    summary = summarize(rows, options.model)
    print(json.dumps({"stopped_early": stopped, **summary}, indent=2))
    if options.no_save:
        return
    now = datetime.now(UTC)
    revision = _git("rev-parse", "HEAD")
    record = {
        "kind": "manual real-model run",
        "provider": settings.llm_provider,
        "requested_model": options.model,
        "run_at": now.isoformat(),
        "code_revision": revision,
        "working_tree_clean": _git("status", "--porcelain") == "",
        "prompt_version": PROMPT_VERSION,
        "evaluation_set_sha256": hashlib.sha256(
            EVALUATION_SET.read_bytes()
        ).hexdigest(),
        "limits": evaluation.limits,
        "stopped_early": stopped,
        "summary": summary,
        "questions": rows,
    }
    path = RESULTS / f"answers-{options.model}-{now:%Y%m%dT%H%M%SZ}-{revision[:7]}.json"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"Saved {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

"""The one-command evaluation's bookkeeping, with no model or database (P6-T1)."""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tests.evaluation.code_state import REPO_ROOT, CodeState, code_state
from tests.evaluation.run_answers import (
    AnswerRun,
    answer_configuration,
    answer_record,
    write_answers,
)
from tests.evaluation.run_evaluation import run_all

from app.services.answering.pipeline import AnswerLimits

LIMITS = AnswerLimits(
    top_k=5,
    max_query_chars=2000,
    max_context_chars=16000,
    max_output_tokens=8000,
    timeout_seconds=60.0,
    malformed_retries=1,
)
STATE = CodeState(revision="abcdef1234567", clean=True)
RUN_AT = datetime(2026, 11, 9, 8, 30, 5, tzinfo=UTC)


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.test", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    (tmp_path / "benchmarks" / "results").mkdir(parents=True)
    (tmp_path / "benchmarks" / "set.json").write_text("{}", encoding="utf-8")
    (tmp_path / "benchmarks" / "results" / "old.json").write_text(
        "{}", encoding="utf-8"
    )
    (tmp_path / "code.py").write_text("x = 1\n", encoding="utf-8")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "first")
    return tmp_path


def test_code_state_reports_the_current_commit(repository: Path) -> None:
    state = code_state(repository)

    assert state == CodeState(git(repository, "rev-parse", "HEAD"), True)


def test_a_new_result_file_does_not_make_the_tree_dirty(repository: Path) -> None:
    (repository / "benchmarks" / "results" / "new.json").write_text(
        "{}", encoding="utf-8"
    )

    assert code_state(repository).clean is True


def test_a_changed_source_file_makes_the_tree_dirty(repository: Path) -> None:
    (repository / "code.py").write_text("x = 2\n", encoding="utf-8")

    assert code_state(repository).clean is False


def test_a_new_source_file_makes_the_tree_dirty(repository: Path) -> None:
    (repository / "other.py").write_text("y = 1\n", encoding="utf-8")

    assert code_state(repository).clean is False


def test_a_changed_evaluation_set_makes_the_tree_dirty(repository: Path) -> None:
    (repository / "benchmarks" / "set.json").write_text("[]", encoding="utf-8")

    assert code_state(repository).clean is False


def test_configuration_records_every_limit_and_the_temperature() -> None:
    assert answer_configuration(LIMITS) == {
        "retriever": "keyword_full_text",
        "top_k": 5,
        "max_query_chars": 2000,
        "max_context_chars": 16000,
        "max_output_tokens": 8000,
        "timeout_seconds": 60.0,
        "malformed_retries": 1,
        "temperature": "provider default",
    }


def record(model: str = "gemini-3.5-flash-lite") -> dict[str, object]:
    return answer_record(
        provider="gemini",
        model=model,
        rows=[],
        stopped="model_rate_limited",
        limits=LIMITS,
        state=STATE,
        run_at=RUN_AT,
        evaluation_limits="small set",
        evaluation_sha256="a" * 64,
    )


def test_record_carries_what_is_needed_to_interpret_the_run() -> None:
    saved = record()

    assert saved["kind"] == "manual real-model run"
    assert saved["provider"] == "gemini"
    assert saved["requested_model"] == "gemini-3.5-flash-lite"
    assert saved["run_at"] == "2026-11-09T08:30:05+00:00"
    assert saved["code_revision"] == "abcdef1234567"
    assert saved["working_tree_clean"] is True
    assert saved["prompt_version"] == "answer-v1"
    assert saved["evaluation_set_sha256"] == "a" * 64
    assert saved["limits"] == "small set"
    assert saved["stopped_early"] == "model_rate_limited"
    assert saved["configuration"] == answer_configuration(LIMITS)
    assert saved["questions"] == []
    assert isinstance(saved["summary"], dict)
    assert saved["summary"]["questions_run"] == 0


def test_a_result_is_saved_under_a_dated_name(tmp_path: Path) -> None:
    saved = record()

    path = write_answers(saved, tmp_path)

    assert path.name == "answers-gemini-3.5-flash-lite-20261109T083005Z-abcdef1.json"
    assert json.loads(path.read_text(encoding="utf-8")) == saved


def test_an_existing_result_is_never_overwritten(tmp_path: Path) -> None:
    path = write_answers(record(), tmp_path)
    before = path.read_bytes()

    with pytest.raises(FileExistsError):
        write_answers(record(), tmp_path)

    assert path.read_bytes() == before


def test_both_evaluations_run_in_order_on_the_same_code_state(tmp_path: Path) -> None:
    calls: list[tuple[str, CodeState]] = []

    def retrieval(state: CodeState) -> Path:
        calls.append(("retrieval", state))
        return tmp_path / "r.json"

    def answers(state: CodeState) -> AnswerRun:
        calls.append(("answers", state))
        return AnswerRun(tmp_path / "a.json", None)

    assert run_all(STATE, retrieval, answers) == 0
    assert calls == [("retrieval", STATE), ("answers", STATE)]


def test_a_run_stopped_early_is_reported_as_a_failure(tmp_path: Path) -> None:
    def retrieval(state: CodeState) -> Path:
        return tmp_path / "r.json"

    def answers(state: CodeState) -> AnswerRun:
        return AnswerRun(tmp_path / "a.json", "model_rate_limited")

    assert run_all(STATE, retrieval, answers) == 1


def test_answers_do_not_start_when_retrieval_fails() -> None:
    started: list[CodeState] = []

    def retrieval(state: CodeState) -> Path:
        raise ValueError("no corpus")

    def answers(state: CodeState) -> AnswerRun:
        started.append(state)
        return AnswerRun(None, None)

    with pytest.raises(ValueError, match="no corpus"):
        run_all(STATE, retrieval, answers)

    assert started == []


@pytest.mark.parametrize(
    "module",
    [
        "tests.evaluation.run_evaluation",
        "tests.evaluation.run_retrieval",
        "tests.evaluation.run_answers",
    ],
)
def test_each_command_starts_outside_pytest(module: str) -> None:
    results = REPO_ROOT / "benchmarks" / "results"
    before = set(results.iterdir())

    done = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        check=False,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert done.returncode == 0, done.stderr
    assert set(results.iterdir()) == before  # --help must not run the evaluation

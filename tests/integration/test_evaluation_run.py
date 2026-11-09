"""The evaluation steps on a real database with a fake model (P6-T1)."""

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.evaluation import run_answers, run_retrieval
from tests.evaluation.code_state import CodeState
from tests.evaluation.dataset import EvaluationSet
from tests.integration.test_keyword_retrieval import add_document
from tests.integration.test_retrieval_harness_run import evaluation_with, sha_of

from app.config import Settings, get_settings
from app.services.llm import FakeModel, ModelRateLimitError

STATE = CodeState(revision="abcdef1234567", clean=False)
INSUFFICIENT = json.dumps(
    {"statements": [], "evidence_sufficiency": "insufficient", "limitations": "None."}
)


def corpus(sessions: sessionmaker[Session]) -> EvaluationSet:
    first = add_document(sessions, "The glaciers retreated because of warming.")
    second = add_document(sessions, "The volcano erupted most recently in spring.")
    return evaluation_with(
        {"p1": sha_of(sessions, first), "p2": sha_of(sessions, second)}
    )


def settings() -> Settings:
    return get_settings().model_copy(update={"llm_provider": "fake-provider"})


def run_with(
    monkeypatch: pytest.MonkeyPatch,
    directory: Path,
    sessions: sessionmaker[Session],
    script: list[Any],
    **options: Any,
) -> tuple[run_answers.AnswerRun, FakeModel]:
    model = FakeModel(script)
    monkeypatch.setattr(run_answers, "build_language_model", lambda _: model)
    monkeypatch.setattr(run_answers, "RESULTS", directory)
    run = run_answers.run_answer_evaluation(
        corpus(sessions), settings(), sessions, STATE, pause=0, **options
    )
    return run, model


def test_a_complete_run_saves_every_answer_with_the_code_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    sessions: sessionmaker[Session],
) -> None:
    run, _ = run_with(monkeypatch, tmp_path, sessions, [INSUFFICIENT, INSUFFICIENT])

    assert run.stopped is None
    assert run.path is not None
    saved = json.loads(run.path.read_text(encoding="utf-8"))
    assert [row["id"] for row in saved["questions"]] == ["q01", "q02"]
    assert saved["code_revision"] == STATE.revision
    assert saved["working_tree_clean"] is False
    assert saved["provider"] == "fake-provider"
    assert saved["configuration"]["top_k"] == get_settings().answer_top_k


def test_a_rate_limit_stops_the_run_and_keeps_what_it_has(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    sessions: sessionmaker[Session],
) -> None:
    run, model = run_with(
        monkeypatch, tmp_path, sessions, [ModelRateLimitError(), INSUFFICIENT]
    )

    assert run.stopped == "model_rate_limited"
    assert len(model.requests) == 1
    assert run.path is not None
    saved = json.loads(run.path.read_text(encoding="utf-8"))
    assert saved["stopped_early"] == "model_rate_limited"
    assert [row["error"] for row in saved["questions"]] == ["model_rate_limited"]


def test_the_limit_runs_only_the_first_questions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    sessions: sessionmaker[Session],
) -> None:
    _, model = run_with(monkeypatch, tmp_path, sessions, [INSUFFICIENT], limit=1)

    assert len(model.requests) == 1


def test_no_save_writes_no_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    sessions: sessionmaker[Session],
) -> None:
    run, _ = run_with(
        monkeypatch, tmp_path, sessions, [INSUFFICIENT, INSUFFICIENT], save=False
    )

    assert run.path is None
    assert list(tmp_path.iterdir()) == []


def test_retrieval_is_saved_with_the_code_state_it_was_given(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    sessions: sessionmaker[Session],
) -> None:
    monkeypatch.setattr(run_retrieval, "RESULTS", tmp_path)

    path = run_retrieval.run_retrieval_evaluation(
        corpus(sessions), settings(), sessions, STATE
    )

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["code_revision"] == STATE.revision
    assert saved["working_tree_clean"] is False
    assert saved["configuration"]["retriever"] == "keyword"

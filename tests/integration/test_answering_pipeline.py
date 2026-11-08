"""One retrieval, one model call, against PostgreSQL (P5-T5; FR-QA-001, AD-006)."""

import json
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_keyword_retrieval import add_document, add_paper
from tests.unit.test_answer_call import VALID, limits

from app.models import Paper
from app.services.answering.pipeline import Answering
from app.services.ingestion.documents import get_paper_titles
from app.services.llm import FakeModel
from app.services.retrieval.keyword import QueryTooLongError, search_passages


def context_of(model: FakeModel) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(model.requests[0].user)
    return data


def spy_on_search(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def spy(*args: Any, **kwargs: Any) -> Any:
        calls.append(args[1])
        return search_passages(*args, **kwargs)

    monkeypatch.setattr("app.services.answering.pipeline.search_passages", spy)
    return calls


def test_one_retrieval_and_one_model_call(
    sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    add_document(sessions, "Glaciers retreated.")
    calls = spy_on_search(monkeypatch)
    model = FakeModel([VALID])

    result = Answering(sessions, model, limits()).ask("Why did glaciers retreat?")

    assert calls == ["Why did glaciers retreat?"]
    assert len(model.requests) == 1
    assert result.attempts == 1
    assert set(result.context.aliases) == {"P1"}


def test_a_retry_does_not_search_again(
    sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    add_document(sessions, "Glaciers retreated.")
    calls = spy_on_search(monkeypatch)

    result = Answering(sessions, FakeModel(["bad", VALID]), limits()).ask("glacier?")

    assert result.attempts == 2
    assert len(calls) == 1


def test_the_model_sees_the_question_and_only_passages_in_scope(
    sessions: sessionmaker[Session],
) -> None:
    wanted = add_document(sessions, "Glaciers in the wanted document.")
    add_document(sessions, "Glaciers in the other document.")
    model = FakeModel([VALID])

    result = Answering(sessions, model, limits()).ask(
        "glacier question", document_ids=[wanted]
    )

    data = context_of(model)
    assert data["question"] == "glacier question"
    assert [p["text"] for p in data["passages"]] == ["Glaciers in the wanted document."]
    assert result.context.aliases["P1"].document_id == wanted


def test_paper_scope_is_applied(sessions: sessionmaker[Session]) -> None:
    paper = add_paper(sessions)
    add_document(sessions, "Glaciers inside.", paper_id=paper)
    add_document(sessions, "Glaciers outside.")
    model = FakeModel([VALID])

    Answering(sessions, model, limits()).ask("glacier", paper_ids=[paper])

    assert [p["text"] for p in context_of(model)["passages"]] == ["Glaciers inside."]


def test_top_k_and_budget_come_from_the_limits(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, *[f"Glaciers retreated {i}." for i in range(6)])

    few = FakeModel([VALID])
    Answering(sessions, few, limits(top_k=2)).ask("glacier")
    assert len(context_of(few)["passages"]) == 2

    tight = FakeModel([VALID])
    result = Answering(sessions, tight, limits(top_k=3, max_context_chars=150)).ask(
        "glacier"
    )
    assert result.context.passages_dropped > 0


def test_the_paper_title_is_labelled(sessions: sessionmaker[Session]) -> None:
    with sessions.begin() as session:
        paper = Paper(metadata_source="grobid", title="Ice Studies")
        session.add(paper)
        session.flush()
        paper_id = paper.id
    add_document(sessions, "Glaciers retreated.", paper_id=paper_id)
    model = FakeModel([VALID])

    Answering(sessions, model, limits()).ask("glacier")

    assert context_of(model)["passages"][0]["paper_title"] == "Ice Studies"


def test_an_over_long_question_is_refused_before_the_model(
    sessions: sessionmaker[Session],
) -> None:
    model = FakeModel([VALID])

    with pytest.raises(QueryTooLongError):
        Answering(sessions, model, limits(max_query_chars=10)).ask("x" * 11)

    assert model.requests == []


def test_get_paper_titles(sessions: sessionmaker[Session]) -> None:
    with sessions.begin() as session:
        named = Paper(metadata_source="grobid", title="Named")
        unnamed = Paper(metadata_source="grobid")
        session.add_all([named, unnamed])
        session.flush()
        ids = (named.id, unnamed.id)

    assert get_paper_titles(sessions, ids) == {ids[0]: "Named", ids[1]: None}
    assert get_paper_titles(sessions, []) == {}

"""One retrieval, one model call, against PostgreSQL (P5-T5; FR-QA-001, AD-006)."""

import json
import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_keyword_retrieval import add_document, add_paper
from tests.unit.test_answer_call import VALID, limits

from app.models import Paper
from app.schemas.answer import MalformedAnswerError
from app.services.answering.pipeline import (
    NOT_PARSED,
    NOTHING_FITS,
    NOTHING_RETRIEVED,
    PARTLY_NOT_PARSED,
    Answering,
)
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


# --- Insufficient evidence (P5-T8, FR-QA-004) ---------------------------------


@pytest.mark.parametrize(
    "question",
    ["volcano eruption", "", "   ", "?!...", "the of and is"],
)
def test_nothing_retrieved_skips_the_model(
    sessions: sessionmaker[Session], question: str
) -> None:
    add_document(sessions, "Glaciers retreated.")
    model = FakeModel([])  # raises if it is ever called

    result = Answering(sessions, model, limits()).ask(question)

    assert model.requests == []
    assert result.answer.evidence_sufficiency == "insufficient"
    assert result.answer.statements == ()
    assert result.answer.limitations == NOTHING_RETRIEVED
    assert result.attempts == 0
    assert (result.model, result.prompt_version) == (None, None)
    assert (result.usage.input_tokens, result.usage.output_tokens) == (0, 0)
    assert result.context.aliases == {}


@pytest.mark.parametrize(
    "scope",
    [{"document_ids": []}, {"paper_ids": []}, {"paper_ids": [uuid.uuid4()]}],
)
def test_an_empty_or_unknown_scope_skips_the_model(
    sessions: sessionmaker[Session], scope: dict[str, Any]
) -> None:
    add_document(sessions, "Glaciers retreated.")
    model = FakeModel([])

    result = Answering(sessions, model, limits()).ask("glacier", **scope)

    assert model.requests == []
    assert result.answer.evidence_sufficiency == "insufficient"


def test_passages_too_long_for_the_budget_skip_the_model_and_say_why(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated. " * 50)
    model = FakeModel([])

    result = Answering(sessions, model, limits(max_context_chars=50)).ask("glacier")

    assert model.requests == []
    assert result.answer.evidence_sufficiency == "insufficient"
    assert result.answer.limitations == NOTHING_FITS
    assert result.context.passages_dropped == 1


# "Not parsed" must not read as "not found" (DR-006).


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_a_scope_with_no_parsed_document_says_so(
    sessions: sessionmaker[Session], status: str
) -> None:
    document = add_document(sessions, "Glaciers retreated.", status=status)
    model = FakeModel([])

    result = Answering(sessions, model, limits()).ask(
        "glacier", document_ids=[document]
    )

    assert model.requests == []
    assert result.answer.evidence_sufficiency == "insufficient"
    assert result.answer.limitations == NOT_PARSED


def test_no_match_in_a_partly_parsed_scope_says_what_was_not_searched(
    sessions: sessionmaker[Session],
) -> None:
    parsed = add_document(sessions, "Rocks only.")
    failed = add_document(sessions, "Glaciers retreated.", status="failed")
    model = FakeModel([])

    result = Answering(sessions, model, limits()).ask(
        "glacier", document_ids=[parsed, failed]
    )

    assert model.requests == []
    assert result.answer.limitations == PARTLY_NOT_PARSED


def test_an_unknown_id_is_not_reported_as_unparsed(
    sessions: sessionmaker[Session],
) -> None:
    result = Answering(sessions, FakeModel([]), limits()).ask(
        "glacier", document_ids=[uuid.uuid4()]
    )

    assert result.answer.limitations == NOTHING_RETRIEVED


def test_an_unparsed_document_outside_the_scope_is_not_mentioned(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated.", status="failed")
    parsed = add_document(sessions, "Rocks only.")
    answering = Answering(sessions, FakeModel([]), limits())

    in_scope = answering.ask("glacier", document_ids=[parsed])
    no_scope = answering.ask("glacier")

    assert in_scope.answer.limitations == NOTHING_RETRIEVED
    assert no_scope.answer.limitations == NOTHING_RETRIEVED


def test_passages_too_long_are_reported_before_an_unparsed_document(
    sessions: sessionmaker[Session],
) -> None:
    parsed = add_document(sessions, "Glaciers retreated. " * 50)
    failed = add_document(sessions, "Rocks only.", status="failed")

    result = Answering(sessions, FakeModel([]), limits(max_context_chars=50)).ask(
        "glacier", document_ids=[parsed, failed]
    )

    assert result.answer.limitations == NOTHING_FITS


def test_the_models_insufficient_answer_is_preserved_without_citations(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated.")
    reply = json.dumps(
        {
            "statements": [],
            "evidence_sufficiency": "insufficient",
            "limitations": "The passages do not cover this.",
        }
    )
    model = FakeModel([reply], model_name="fake-b")

    result = Answering(sessions, model, limits()).ask("glacier cost")

    assert len(model.requests) == 1
    assert result.answer.statements == ()
    assert result.answer.limitations == "The passages do not cover this."
    assert result.model == "fake-b"
    assert result.prompt_version is not None


def test_an_insufficient_answer_with_statements_is_not_accepted(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated.")
    reply = json.dumps(
        {
            "statements": [
                {"text": "A guess.", "citations": [{"alias": "P1", "quote": None}]}
            ],
            "evidence_sufficiency": "insufficient",
            "limitations": None,
        }
    )

    with pytest.raises(MalformedAnswerError):
        Answering(sessions, FakeModel([reply, reply]), limits()).ask("glacier")


# --- The full chain with the fake model (P5-T9) -------------------------------


def stored_answer(
    *citations: dict[str, object], sufficiency: str = "sufficient"
) -> str:
    return json.dumps(
        {
            "statements": [{"text": "Ice retreated.", "citations": list(citations)}],
            "evidence_sufficiency": sufficiency,
            "limitations": None,
        }
    )


def test_full_chain_returns_validated_evidence_from_the_database(
    sessions: sessionmaker[Session],
) -> None:
    document_id = add_document(
        sessions,
        {
            "text": "Glaciers retreated quickly.",
            "section_title": "Results",
            "page_start": 7,
            "page_end": 7,
        },
    )
    reply = stored_answer({"alias": "P1", "quote": "retreated quickly"})

    result = Answering(
        sessions, FakeModel([reply], model_name="fake-z"), limits()
    ).answer("glacier", document_ids=[document_id])

    assert result.validation_status == "validated"
    assert result.model == "fake-z"
    assert result.claim_support == "not_evaluated"
    [evidence] = result.evidence
    assert (evidence.section, evidence.page_start) == ("Results", 7)
    assert evidence.document_id == document_id
    assert len(result.retrieved_passage_ids) == 1


def test_full_chain_marks_an_invalid_citation_as_failed(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated quickly.")
    reply = stored_answer({"alias": "P9", "quote": None})

    result = Answering(sessions, FakeModel([reply]), limits()).answer("glacier")

    assert result.validation_status == "failed"
    assert result.evidence == ()
    assert result.statements[0].citations[0].reason == "passage_not_found"


def test_full_chain_applies_the_scope_to_citations(
    sessions: sessionmaker[Session],
) -> None:
    paper = add_paper(sessions)
    add_document(sessions, "Glaciers inside.", paper_id=paper)
    reply = stored_answer({"alias": "P1", "quote": None})

    result = Answering(sessions, FakeModel([reply]), limits()).answer(
        "glacier", paper_ids=[paper]
    )

    assert result.validation_status == "validated"
    assert result.evidence[0].paper_id == paper


def test_full_chain_with_nothing_retrieved_is_insufficient_and_validated(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, "Glaciers retreated.")
    model = FakeModel([])

    result = Answering(sessions, model, limits()).answer("volcano")

    assert model.requests == []
    assert result.evidence_sufficiency == "insufficient"
    assert result.limitations == NOTHING_RETRIEVED
    assert result.validation_status == "validated"
    assert result.model is None
    assert result.evidence == ()


@pytest.mark.parametrize("scope_by", ["document_ids", "paper_ids"])
def test_scope_is_checked_again_even_if_retrieval_leaks(
    sessions: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    scope_by: str,
) -> None:
    """A retrieval bug must surface as a failed citation, not as evidence."""
    wanted = add_paper(sessions)
    wanted_document = add_document(sessions, "Rocks only.", paper_id=wanted)
    add_document(sessions, "Glaciers elsewhere.")

    def leaky(*args: Any, **kwargs: Any) -> Any:
        kwargs.update(document_ids=None, paper_ids=None)
        return search_passages(*args, **kwargs)

    monkeypatch.setattr("app.services.answering.pipeline.search_passages", leaky)
    scope = {"document_ids": [wanted_document], "paper_ids": [wanted]}[scope_by]
    reply = stored_answer({"alias": "P1", "quote": None})

    result = Answering(sessions, FakeModel([reply]), limits()).answer(
        "glacier", **{scope_by: scope}
    )

    assert result.validation_status == "failed"
    assert result.statements[0].citations[0].reason == "wrong_paper"
    assert result.evidence == ()

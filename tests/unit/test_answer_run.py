"""The real-model run script's bookkeeping, with no model or network (P5-T12)."""

import uuid
from typing import Any

from tests.evaluation.dataset import Question
from tests.evaluation.retrieval_harness import StoredPassage
from tests.evaluation.run_answers import TrackingModel, run_question, summarize

from app.schemas.answer_response import (
    AnswerResponse,
    CitationResponse,
    EvidencePassage,
    StatementResponse,
)
from app.services.llm import FakeModel, ModelRateLimitError, ModelRequest, ModelUsage

QUOTE = "the quoted sentence from the paper"
DOCUMENT = uuid.uuid4()
RIGHT = StoredPassage(uuid.uuid4(), DOCUMENT, f"Text {QUOTE}.")
WRONG = StoredPassage(uuid.uuid4(), DOCUMENT, "Something else entirely.")
PASSAGES = {"p1": [RIGHT, WRONG]}
ANSWERABLE = Question(
    id="q01",
    question="A question of some length?",
    answerable=True,
    papers=["p1"],
    expected_quotes=[{"paper": "p1", "quote": QUOTE}],
)
UNANSWERABLE = Question(
    id="q02",
    question="An unanswerable question?",
    answerable=False,
    papers=[],
    expected_quotes=[],
)
REQUEST = ModelRequest("s", "u", {}, 10, 1.0)


def response(cited: StoredPassage | None, **values: Any) -> AnswerResponse:
    statements: tuple[StatementResponse, ...] = ()
    evidence: tuple[EvidencePassage, ...] = ()
    if cited is not None:
        statements = (
            StatementResponse(
                text="A claim.",
                has_valid_citation=True,
                citations=(
                    CitationResponse(
                        alias="P1",
                        quote=None,
                        valid=True,
                        reason=None,
                        passage_id=cited.passage_id,
                    ),
                ),
            ),
        )
        evidence = (
            EvidencePassage(
                alias="P1",
                passage_id=cited.passage_id,
                document_id=DOCUMENT,
                paper_id=uuid.uuid4(),
                paper_title=None,
                section=None,
                page_start=None,
                page_end=None,
                text=cited.text,
            ),
        )
    fields: dict[str, Any] = {
        "statements": statements,
        "evidence": evidence,
        "evidence_sufficiency": "sufficient" if statements else "insufficient",
        "limitations": None,
        "validation_status": "validated",
        "claim_support": "not_evaluated",
        "retrieved_passage_ids": (RIGHT.passage_id, WRONG.passage_id),
        "passages_dropped": 0,
        "retrieval_method": "keyword_full_text",
        "model": "fake",
        "prompt_version": "answer-v1",
        **values,
    }
    return AnswerResponse(**fields)


def tracker(*script: Any) -> TrackingModel:
    return TrackingModel(FakeModel(list(script), usage=ModelUsage(100, 50)))


def run(
    track: TrackingModel, question: Question, result: AnswerResponse
) -> dict[str, Any]:
    def answer(text: str, ids: list[uuid.UUID]) -> AnswerResponse:
        track.generate(REQUEST)
        return result

    return run_question(answer, track, question, [DOCUMENT], PASSAGES)


def test_a_call_records_tokens_and_time() -> None:
    track = tracker("output")

    assert track.generate(REQUEST).text == "output"

    [call] = track.calls
    assert (call.input_tokens, call.output_tokens) == (100, 50)
    assert call.seconds >= 0


def test_citing_the_expected_passage_is_recorded() -> None:
    row = run(tracker("x"), ANSWERABLE, response(RIGHT))

    assert (row["expected_retrieved"], row["expected_cited"]) == (True, True)
    assert (row["model_calls"], row["input_tokens"], row["output_tokens"]) == (
        1,
        100,
        50,
    )


def test_citing_another_passage_is_not_counted_as_the_expected_one() -> None:
    row = run(tracker("x"), ANSWERABLE, response(WRONG))

    assert (row["expected_retrieved"], row["expected_cited"]) == (True, False)


def test_a_model_failure_is_recorded_and_not_raised() -> None:
    track = tracker(ModelRateLimitError())

    def answer(text: str, ids: list[uuid.UUID]) -> AnswerResponse:
        track.generate(REQUEST)
        raise AssertionError("not reached")

    row = run_question(answer, track, ANSWERABLE, [DOCUMENT], PASSAGES)

    assert row["error"] == "model_rate_limited"
    assert "validation_status" not in row


def test_each_question_counts_only_its_own_calls() -> None:
    track = tracker("a", "b")

    run(track, ANSWERABLE, response(RIGHT))
    row = run(track, ANSWERABLE, response(RIGHT))

    assert row["model_calls"] == 1


def test_summary_separates_answerable_from_unanswerable() -> None:
    track = tracker("a", "b", "c", "d")
    rows = [
        run(track, ANSWERABLE, response(RIGHT)),
        run(track, ANSWERABLE, response(WRONG, validation_status="failed")),
        run(track, UNANSWERABLE, response(None)),
        run(track, UNANSWERABLE, response(WRONG)),
    ]

    summary = summarize(rows, "gemini-3.8-flash")

    assert summary["answerable"] == {
        "total": 2,
        "errors": 0,
        "validated_with_statements": 1,
        "failed_validation": 1,
        "said_insufficient": 0,
        "expected_passage_retrieved": 2,
        "expected_passage_cited": 1,
    }
    assert summary["unanswerable"] == {
        "total": 2,
        "errors": 0,
        "said_insufficient": 1,
        "gave_statements": 1,
        "failed_validation": 0,
    }
    assert (summary["input_tokens"], summary["output_tokens"]) == (400, 200)
    # (100 x 0.75 + 50 x 3.75) per million = 0.0002625 per answer
    assert summary["paid_equivalent_usd_per_answer"] == 0.00026


def test_summary_with_no_calls_has_no_averages() -> None:
    summary = summarize([], "unknown-model")

    assert summary["mean_model_seconds"] is None
    assert summary["paid_equivalent_usd_per_answer"] is None

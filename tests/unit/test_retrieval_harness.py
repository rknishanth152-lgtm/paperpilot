"""The retrieval harness, with a fake retriever (P4-T6, FR-EVL-002). No database."""

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from tests.evaluation.dataset import EvaluationSet, load_evaluation_set
from tests.evaluation.retrieval_harness import (
    Retriever,
    StoredPassage,
    evaluate,
    normalize_for_matching,
    require_reviewed,
    result_record,
    write_result,
)

P1, P2 = "p1", "p2"
DOCUMENTS = {P1: uuid.uuid4(), P2: uuid.uuid4()}
ALL_DOCUMENTS = list(DOCUMENTS.values())


@dataclass(frozen=True)
class Found:
    passage_id: uuid.UUID
    score: float = 0.5


def stored(paper: str, body: str) -> StoredPassage:
    return StoredPassage(uuid.uuid4(), DOCUMENTS[paper], body)


def question(
    qid: str, paper: str, *quotes: str, text: str = "A question of some length?"
) -> dict[str, object]:
    return {
        "id": qid,
        "question": text,
        "answerable": True,
        "papers": [paper],
        "expected_quotes": [{"paper": paper, "quote": q} for q in quotes],
    }


def unanswerable(qid: str) -> dict[str, object]:
    return {
        "id": qid,
        "question": "A question with no answer?",
        "answerable": False,
        "papers": [],
        "expected_quotes": [],
    }


def evaluation_set(*questions: dict[str, object], **values: object) -> EvaluationSet:
    return EvaluationSet.model_validate(
        {
            "name": "n",
            "version": 3,
            "status": "reviewed",
            "created": "2026-11-08",
            "drafted_by": "d",
            "reviewer": "someone",
            "review_date": "2026-11-08",
            "limits": "small",
            "corpus": [
                {"key": k, "title": "t", "doi": "d", "licence": "l", "sha256": "a" * 64}
                for k in DOCUMENTS
            ],
            "excluded_probe_queries": [],
            "questions": list(questions),
            **values,
        }
    )


QUOTE = "the quoted sentence from the paper"
ANSWER = stored(P1, f"Before {QUOTE} after.")
OTHER = stored(P1, "An unrelated passage about something else entirely.")
PASSAGES = {P1: [ANSWER, OTHER], P2: []}


def retriever(*ranked: uuid.UUID) -> Retriever:
    def retrieve(text: str, k: int, document_ids: Sequence[uuid.UUID]) -> list[Found]:
        return [Found(passage_id) for passage_id in ranked]

    return retrieve


def run(evaluation: EvaluationSet, *ranked: uuid.UUID, k: int = 5) -> dict[str, Any]:
    return evaluate(evaluation, DOCUMENTS, PASSAGES, retriever(*ranked), k=k)


# --- Normalisation (provisional OQ-013 rules) ---------------------------------


@pytest.mark.parametrize(
    ("text", "normalized"),
    [
        ("a   b\n c", "a b c"),
        ("conﬁrmation", "confirmation"),
        ("confi rmation", "confirmation"),
        ("inﬂuence and infl uence", "influence and influence"),
        ("“quoted” ‘x’", "\"quoted\" 'x'"),
        ("a–b—c−d", "a-b-c-d"),
    ],
)
def test_normalize_for_matching(text: str, normalized: str) -> None:
    assert normalize_for_matching(text) == normalized


def test_normalisation_keeps_case() -> None:
    assert normalize_for_matching("Glacier") != normalize_for_matching("glacier")


# --- Outcomes -----------------------------------------------------------------


def test_expected_passage_in_the_top_5_is_a_hit() -> None:
    result = run(
        evaluation_set(question("q01", P1, QUOTE)), OTHER.passage_id, ANSWER.passage_id
    )

    [row] = result["questions"]
    assert row["outcome"] == "hit"
    assert row["rank_all_papers"] == 2
    assert row["expected_passage_ids"] == [str(ANSWER.passage_id)]
    assert result["summary"]["hits_all_papers"] == 1
    assert result["summary"]["recall_at_k_all_papers"] == 1.0


def test_expected_passage_not_retrieved_is_a_miss() -> None:
    result = run(evaluation_set(question("q01", P1, QUOTE)), OTHER.passage_id)

    [row] = result["questions"]
    assert (row["outcome"], row["rank_all_papers"]) == ("miss", None)
    assert result["summary"]["recall_at_k_all_papers"] == 0.0


def test_rank_beyond_k_is_a_miss_even_if_the_retriever_returns_more() -> None:
    fillers = [uuid.uuid4() for _ in range(5)]

    result = run(
        evaluation_set(question("q01", P1, QUOTE)), *fillers, ANSWER.passage_id
    )

    assert result["questions"][0]["outcome"] == "miss"


def test_any_expected_passage_counts() -> None:
    second = "another quoted sentence in the same paper"
    other_answer = stored(P1, f"Text {second}.")
    passages = {P1: [ANSWER, other_answer], P2: []}

    result = evaluate(
        evaluation_set(question("q01", P1, QUOTE, second)),
        DOCUMENTS,
        passages,
        retriever(other_answer.passage_id),
    )

    assert result["questions"][0]["outcome"] == "hit"


def test_a_quote_is_only_looked_for_in_its_own_paper() -> None:
    passages = {P1: [], P2: [stored(P2, f"Text {QUOTE}.")]}

    result = evaluate(
        evaluation_set(question("q01", P1, QUOTE)),
        DOCUMENTS,
        passages,
        retriever(passages[P2][0].passage_id),
    )

    assert result["questions"][0]["outcome"] == "unmatched"


# --- Unmatched expectations are labelling errors, not misses ------------------


def test_unmatched_quote_is_reported_and_not_counted_as_a_miss() -> None:
    evaluation = evaluation_set(
        question("q01", P1, QUOTE),
        question("q02", P1, "this quote does not exist anywhere"),
    )

    result = run(evaluation, ANSWER.passage_id)

    assert [row["outcome"] for row in result["questions"]] == ["hit", "unmatched"]
    assert result["questions"][1]["unmatched_quotes"] == [
        "this quote does not exist anywhere"
    ]
    summary = result["summary"]
    assert (
        summary["answerable"],
        summary["evaluated"],
        summary["unmatched_questions"],
    ) == (2, 1, 1)
    assert summary["recall_at_k_all_papers"] == 1.0


def test_partly_matched_question_is_evaluated_and_lists_the_bad_quote() -> None:
    evaluation = evaluation_set(
        question("q01", P1, QUOTE, "this quote does not exist anywhere")
    )

    result = run(evaluation, ANSWER.passage_id)

    [row] = result["questions"]
    assert row["outcome"] == "hit"
    assert row["unmatched_quotes"] == ["this quote does not exist anywhere"]
    assert result["summary"]["unmatched_quotes"] == 1
    assert result["summary"]["unmatched_questions"] == 0


def test_recall_is_none_when_nothing_could_be_evaluated() -> None:
    result = run(evaluation_set(unanswerable("q01")))

    assert result["summary"]["evaluated"] == 0
    assert result["summary"]["recall_at_k_all_papers"] is None


# --- Unanswerable questions and scopes ----------------------------------------


def test_unanswerable_questions_are_listed_but_not_scored() -> None:
    evaluation = evaluation_set(question("q01", P1, QUOTE), unanswerable("q02"))

    result = run(evaluation, ANSWER.passage_id, OTHER.passage_id)

    row = result["questions"][1]
    assert row["outcome"] == "unanswerable"
    assert row["returned_all_papers"] == 2
    assert result["summary"]["evaluated"] == 1
    assert result["summary"]["recall_at_k_all_papers"] == 1.0


def test_each_question_is_searched_across_the_corpus_and_within_its_paper() -> None:
    calls: list[tuple[str, int, list[uuid.UUID]]] = []

    def retrieve(text: str, k: int, document_ids: Sequence[uuid.UUID]) -> list[Found]:
        calls.append((text, k, list(document_ids)))
        return [] if len(document_ids) > 1 else [Found(ANSWER.passage_id)]

    result = evaluate(
        evaluation_set(question("q01", P1, QUOTE, text="What is the actual question?")),
        DOCUMENTS,
        PASSAGES,
        retrieve,
        k=5,
    )

    assert calls == [
        ("What is the actual question?", 5, ALL_DOCUMENTS),
        ("What is the actual question?", 5, [DOCUMENTS[P1]]),
    ]
    [row] = result["questions"]
    assert row["outcome"] == "miss"  # the main figure is the harder, whole-corpus one
    assert row["rank_question_paper"] == 1
    summary = result["summary"]
    assert (
        summary["recall_at_k_all_papers"],
        summary["recall_at_k_question_paper"],
    ) == (0.0, 1.0)


# --- Review gate and the saved result -----------------------------------------


def test_a_draft_set_is_refused() -> None:
    draft = evaluation_set(status="draft", reviewer=None, review_date=None)

    with pytest.raises(ValueError, match="not been reviewed"):
        require_reviewed(draft)


def test_reviewed_set_is_accepted() -> None:
    require_reviewed(evaluation_set())


def record(evaluation: EvaluationSet) -> dict[str, Any]:
    return result_record(
        run(evaluation, ANSWER.passage_id),
        evaluation=evaluation,
        evaluation_sha256="f" * 64,
        run_at=datetime(2026, 11, 8, 12, 30, 5, tzinfo=UTC),
        code_revision="abcdef1234567890",
        working_tree_clean=False,
        configuration={"k": 5, "ranking": "ts_rank"},
    )


def test_result_records_date_revision_configuration_and_limits() -> None:
    saved = record(evaluation_set(question("q01", P1, QUOTE)))

    assert saved["run_at"] == "2026-11-08T12:30:05+00:00"
    assert saved["code_revision"] == "abcdef1234567890"
    assert saved["working_tree_clean"] is False
    assert saved["configuration"] == {"k": 5, "ranking": "ts_rank"}
    assert saved["evaluation_set"] == {
        "version": 3,
        "sha256": "f" * 64,
        "status": "reviewed",
        "reviewer": "someone",
        "review_date": "2026-11-08",
        "questions": 1,
    }
    assert saved["limits"] == "small"
    assert saved["summary"]["evaluated"] == 1


def test_result_is_written_to_a_new_dated_file(tmp_path: Path) -> None:
    saved = record(evaluation_set(question("q01", P1, QUOTE)))

    path = write_result(saved, tmp_path)

    assert path.name == "retrieval-20261108T123005Z-abcdef1.json"
    assert json.loads(path.read_text(encoding="utf-8")) == saved
    with pytest.raises(FileExistsError):
        write_result(saved, tmp_path)


def test_the_real_set_is_reviewed_and_named() -> None:
    evaluation = load_evaluation_set()

    require_reviewed(evaluation)
    assert evaluation.reviewer

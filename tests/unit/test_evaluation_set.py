"""The evaluation set file meets FR-EVL-001 (P4-T5). No database needed."""

import pytest
from pydantic import ValidationError
from tests.evaluation.dataset import EvaluationSet, Question, load_evaluation_set


def test_the_set_meets_the_requirement() -> None:
    evaluation = load_evaluation_set()
    answerable = [q for q in evaluation.questions if q.answerable]
    papers = {paper for q in answerable for paper in q.papers}

    assert 18 <= len(evaluation.questions) <= 25  # "about 20"
    assert len(papers) >= 3
    assert len(answerable) < len(evaluation.questions)  # some are unanswerable


def test_no_question_was_used_as_a_configuration_probe() -> None:
    """The probes' results were seen in P4-T1 (docs/design/retrieval.md §5)."""
    evaluation = load_evaluation_set()
    probes = {probe.casefold() for probe in evaluation.excluded_probe_queries}

    assert len(probes) == 6
    assert not probes & {q.question.casefold() for q in evaluation.questions}


def question(**values: object) -> dict[str, object]:
    return {
        "id": "q01",
        "question": "A question of some length?",
        "answerable": True,
        "papers": ["p1"],
        "expected_quotes": [{"paper": "p1", "quote": "a quote that is long enough"}],
        **values,
    }


def test_valid_question_is_accepted() -> None:
    assert Question.model_validate(question()).answerable


@pytest.mark.parametrize(
    "values",
    [
        {"expected_quotes": []},
        {"answerable": False},
        {"answerable": False, "expected_quotes": []},  # still lists a paper
        {"papers": ["p2"]},  # the quote is from a paper not listed
        {"expected_quotes": [{"paper": "p1", "quote": "too short"}]},
        {"extra": "field"},
    ],
)
def test_inconsistent_question_is_rejected(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Question.model_validate(question(**values))


def evaluation_set(**values: object) -> dict[str, object]:
    return {
        "name": "n",
        "version": 1,
        "status": "draft",
        "created": "2026-11-08",
        "drafted_by": "d",
        "reviewer": None,
        "review_date": None,
        "limits": "l",
        "corpus": [
            {"key": "p1", "title": "t", "doi": "d", "licence": "l", "sha256": "a" * 64}
        ],
        "excluded_probe_queries": [],
        "questions": [question()],
        **values,
    }


def test_valid_set_is_accepted() -> None:
    assert EvaluationSet.model_validate(evaluation_set()).status == "draft"


@pytest.mark.parametrize(
    "values",
    [
        {"status": "reviewed"},  # no reviewer
        {"reviewer": "someone", "review_date": "2026-11-08"},  # still "draft"
        {"questions": [question(), question()]},  # duplicate id
        {
            "questions": [
                question(
                    papers=["p9"],
                    expected_quotes=[{"paper": "p9", "quote": "long enough quote"}],
                )
            ]
        },
    ],
)
def test_inconsistent_set_is_rejected(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EvaluationSet.model_validate(evaluation_set(**values))

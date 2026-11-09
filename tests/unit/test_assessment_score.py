"""Scoring checklist statuses against hand labels (R8; FR-EVL-006). Pure."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from tests.evaluation.code_state import CodeState
from tests.evaluation.score_assessment import (
    Pair,
    pairs_from,
    score,
    score_record,
    write_score,
)

STATE = CodeState(revision="abcdef1234567", clean=True)
RUN_AT = datetime(2026, 11, 9, 8, 30, 5, tzinfo=UTC)
R, P, N, V = "reported", "partially_reported", "not_found", "needs_review"


def pairs(*values: tuple[str, str]) -> list[Pair]:
    return [
        Pair(paper="p1", item=f"i{n}", labelled=labelled, assessed=assessed)
        for n, (labelled, assessed) in enumerate(values)
    ]


def test_agreement_is_counted_over_all_items() -> None:
    result = score(pairs((R, R), (R, N), (N, N), (N, R)))

    assert result["items"] == 4
    assert result["agreements"] == 2
    assert result["agreement_rate"] == 0.5


def test_each_status_reports_its_own_counts() -> None:
    result = score(pairs((R, R), (R, N), (N, N)))

    assert result["per_status"][R] == {
        "labelled": 2,
        "assessed": 1,
        "agreed": 1,
        "recall": 0.5,
        "precision": 1.0,
    }
    assert result["per_status"][N] == {
        "labelled": 1,
        "assessed": 2,
        "agreed": 1,
        "recall": 1.0,
        "precision": 0.5,
    }


def test_a_status_with_no_labels_is_not_measurable() -> None:
    result = score(pairs((R, V), (R, R)))

    assert result["per_status"][V]["labelled"] == 0
    assert result["per_status"][V]["recall"] is None
    assert result["per_status"][V]["precision"] == 0.0
    assert result["per_status"][P]["recall"] is None
    assert result["per_status"][P]["precision"] is None


def test_the_confusion_table_covers_every_pair_of_statuses() -> None:
    table = score(pairs((R, N), (R, N), (N, V)))["confusion"]

    assert table[R][N] == 2
    assert table[N][V] == 1
    assert table[R][R] == 0
    assert set(table) == {R, P, N, V}
    assert all(set(row) == {R, P, N, V} for row in table.values())


def test_not_found_and_needs_review_confusion_is_reported() -> None:
    result = score(pairs((N, V), (N, V), (V, N), (N, N)))

    assert result["not_found_vs_needs_review"] == {
        "labelled_not_found_assessed_needs_review": 2,
        "labelled_needs_review_assessed_not_found": 1,
        "measurable": True,
    }


@pytest.mark.parametrize(
    "values",
    [
        pytest.param([(R, R), (N, V)], id="no needs_review labels"),
        pytest.param([(R, R), (V, V)], id="no not_found labels"),
    ],
)
def test_that_confusion_is_unmeasurable_without_both_labels(
    values: list[tuple[str, str]],
) -> None:
    assert score(pairs(*values))["not_found_vs_needs_review"]["measurable"] is False


def test_always_giving_the_commonest_label_is_the_baseline() -> None:
    result = score(pairs((R, N), (R, N), (R, R), (N, N)))

    assert result["majority_baseline"] == {
        "label": R,
        "agreements": 3,
        "rate": 0.75,
    }


def test_a_tie_for_the_commonest_label_is_stable() -> None:
    assert score(pairs((N, N), (R, R)))["majority_baseline"]["label"] == R


def test_overstated_and_understated_are_separate() -> None:
    result = score(pairs((N, R), (N, P), (P, R), (R, N), (R, P), (P, N), (R, R)))

    assert result["overstated"] == 3
    assert result["understated"] == 3


def test_overstating_is_claiming_more_than_the_label() -> None:
    result = score(pairs((N, R), (N, P), (R, N)))

    assert (result["overstated"], result["understated"]) == (2, 1)


def test_needs_review_is_neither_overstated_nor_understated() -> None:
    result = score(pairs((R, V), (N, V), (V, R), (V, N)))

    assert (result["overstated"], result["understated"]) == (0, 0)


def test_nothing_to_score_is_refused() -> None:
    with pytest.raises(ValueError):
        score([])


class _Item:
    def __init__(self, key: str, status: str) -> None:
        self.key = key
        self.status = status


class _Assessment:
    def __init__(self, *items: _Item) -> None:
        self.items = items


class _Labels:
    def __init__(self, *rows: tuple[str, str, str]) -> None:
        self.labels = [_Label(*row) for row in rows]


class _Label:
    def __init__(self, paper: str, item: str, status: str) -> None:
        self.paper = paper
        self.item = item
        self.status = status


def test_labels_are_matched_to_assessments_by_paper_and_item() -> None:
    labels: Any = _Labels(("p1", "a", R), ("p2", "a", N))
    assessed: Any = {
        "p1": _Assessment(_Item("a", N)),
        "p2": _Assessment(_Item("a", R)),
    }

    assert pairs_from(labels, assessed) == [
        Pair("p1", "a", R, N),
        Pair("p2", "a", N, R),
    ]


def test_a_missing_assessment_item_is_refused() -> None:
    labels: Any = _Labels(("p1", "b", R))
    assessed: Any = {"p1": _Assessment(_Item("a", R))}

    with pytest.raises(KeyError):
        pairs_from(labels, assessed)


def record() -> dict[str, Any]:
    return score_record(
        pairs((R, R)),
        rows=[{"paper": "p1", "item": "i0"}],
        labels_sha256="1" * 64,
        guide_sha256="2" * 64,
        checklist_version="checklist-v1",
        model="m",
        prompt_version="v",
        retrieval_method="semantic_cosine",
        labeller="someone",
        labelled_on="2026-11-09",
        run_at=RUN_AT,
        state=STATE,
    )


def test_a_saved_score_says_what_produced_it() -> None:
    saved = record()

    assert saved["kind"] == "manual real-model run, reproducibility checklist"
    assert saved["code_revision"] == STATE.revision
    assert saved["working_tree_clean"] is True
    assert saved["labels_sha256"] == "1" * 64
    assert saved["guide_sha256"] == "2" * 64
    assert saved["checklist_version"] == "checklist-v1"
    assert (saved["model"], saved["prompt_version"]) == ("m", "v")
    assert saved["retrieval_method"] == "semantic_cosine"
    assert (saved["labeller"], saved["labelled_on"]) == ("someone", "2026-11-09")
    assert saved["result"]["items"] == 1
    assert saved["items"] == [{"paper": "p1", "item": "i0"}]
    assert "one labeller" in saved["limits"]


def test_a_score_is_written_to_a_new_dated_file(tmp_path: Path) -> None:
    saved = record()

    path = write_score(saved, tmp_path)

    assert path.name == "reproducibility-score-20261109T083005Z-abcdef1.json"
    assert json.loads(path.read_text(encoding="utf-8")) == saved
    with pytest.raises(FileExistsError):
        write_score(saved, tmp_path)

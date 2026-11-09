"""Reciprocal Rank Fusion with fixed ranked lists (R3; FR-RET-006). Pure and offline."""

import uuid

import pytest

from app.services.retrieval.hybrid import reciprocal_rank_fusion
from app.services.retrieval.keyword import RetrievedPassage


def passage(name: int, score: float = 0.5) -> RetrievedPassage:
    return RetrievedPassage(
        passage_id=uuid.UUID(int=name),
        document_id=uuid.UUID(int=1000),
        paper_id=uuid.UUID(int=2000),
        section=None,
        page_start=None,
        page_end=None,
        text=f"Passage {name}.",
        score=score,
    )


A, B, C, D, E, F, G = (passage(n) for n in range(1, 8))


def ids(passages: list[RetrievedPassage]) -> list[int]:
    return [p.passage_id.int for p in passages]


def test_a_passage_in_both_lists_beats_one_in_a_single_list() -> None:
    fused = reciprocal_rank_fusion([[A, B], [C, B]], k=3, constant=60)

    assert ids(fused)[0] == 2


def test_the_score_is_the_sum_of_reciprocal_ranks() -> None:
    fused = reciprocal_rank_fusion([[A, B], [B]], k=2, constant=10)

    scores = {p.passage_id.int: p.score for p in fused}
    assert scores[2] == pytest.approx(1 / 12 + 1 / 11)
    assert scores[1] == pytest.approx(1 / 11)


def test_original_scores_do_not_influence_the_order() -> None:
    huge = passage(1, score=1000.0)
    tiny = passage(2, score=0.001)

    assert ids(reciprocal_rank_fusion([[tiny, huge]], k=2, constant=60)) == [2, 1]


def test_ties_are_broken_by_passage_id() -> None:
    fused = reciprocal_rank_fusion([[D], [A]], k=2, constant=60)

    assert ids(fused) == [1, 4]


def test_the_constant_changes_how_much_rank_matters() -> None:
    first_list = [A, B, C, G]
    second_list = [D, E, F, G]

    steep = reciprocal_rank_fusion([first_list, second_list], k=1, constant=1)
    flat = reciprocal_rank_fusion([first_list, second_list], k=1, constant=1000)

    assert ids(steep) == [1]
    assert ids(flat) == [7]


def test_the_result_is_limited_to_k() -> None:
    assert ids(reciprocal_rank_fusion([[A, B, C]], k=2, constant=60)) == [1, 2]


def test_one_empty_list_leaves_the_other_in_order() -> None:
    assert ids(reciprocal_rank_fusion([[], [C, A]], k=5, constant=60)) == [3, 1]


def test_nothing_in_gives_nothing_out() -> None:
    assert reciprocal_rank_fusion([[], []], k=5, constant=60) == []


def test_the_passage_details_are_kept() -> None:
    [fused] = reciprocal_rank_fusion([[A]], k=1, constant=60)

    assert fused.text == A.text
    assert fused.passage_id == A.passage_id


@pytest.mark.parametrize(("k", "constant"), [(0, 60), (5, 0), (5, -1)])
def test_bad_settings_are_refused(k: int, constant: int) -> None:
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([[A]], k=k, constant=constant)

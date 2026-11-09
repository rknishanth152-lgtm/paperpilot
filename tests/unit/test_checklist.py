"""The versioned reproducibility checklist (R5; FR-REP-001, OQ-010)."""

import re

from app.models.constraints import REPRODUCIBILITY_STATUSES
from app.services.reproducibility.checklist import CHECKLIST, CHECKLIST_VERSION


def test_the_checklist_has_a_version() -> None:
    assert CHECKLIST_VERSION == "checklist-v1"


def test_the_first_version_is_small_and_has_unique_snake_case_keys() -> None:
    keys = [item.key for item in CHECKLIST]

    assert 5 <= len(keys) <= 8
    assert len(set(keys)) == len(keys)
    assert all(re.fullmatch(r"[a-z]+(_[a-z]+)*", key) for key in keys)


def test_every_item_says_what_counts() -> None:
    for item in CHECKLIST:
        assert item.title
        assert item.question.endswith("?")
        assert item.reported
        assert item.partially_reported
        assert item.reported != item.partially_reported


def test_the_statuses_are_exactly_the_four_defined() -> None:
    assert REPRODUCIBILITY_STATUSES == (
        "reported",
        "partially_reported",
        "not_found",
        "needs_review",
    )


def test_no_item_uses_verdict_language() -> None:
    forbidden = ("irreproducible", "reproducible", "score", "grade", "verdict")
    for item in CHECKLIST:
        parts = (item.title, item.question, item.reported, item.partially_reported)
        text = " ".join(parts).lower()
        assert not any(word in text for word in forbidden), item.key

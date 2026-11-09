"""The words shown for each status (R7; FR-REP-004). Pure."""

import re

import pytest

from app.models.constraints import (
    REPRODUCIBILITY_REVIEW_REASONS,
    REPRODUCIBILITY_STATUSES,
)
from app.services.reproducibility.wording import status_text


def all_cases() -> list[tuple[str, str | None]]:
    plain = [(s, None) for s in REPRODUCIBILITY_STATUSES if s != "needs_review"]
    return [*plain, *(("needs_review", r) for r in REPRODUCIBILITY_REVIEW_REASONS)]


@pytest.mark.parametrize(("status", "reason"), all_cases())
def test_every_status_has_plain_words_and_no_verdict(
    status: str, reason: str | None
) -> None:
    label, description = status_text(status, reason)

    assert label
    assert description
    assert not re.search(
        r"reproducib|irreproduc|score|grade|verdict|\bfail|\bpass(ed|es)?\b",
        f"{label} {description}".lower(),
    )


def test_not_found_is_about_the_material_examined() -> None:
    label, description = status_text("not_found", None)

    assert label == "Not found in the material examined"
    assert "does not mean" in description


def test_each_review_reason_reads_differently() -> None:
    texts = {status_text("needs_review", r)[1] for r in REPRODUCIBILITY_REVIEW_REASONS}

    assert len(texts) == len(REPRODUCIBILITY_REVIEW_REASONS)

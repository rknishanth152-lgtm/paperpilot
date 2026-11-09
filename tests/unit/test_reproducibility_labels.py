"""The reproducibility labelling sheet and labels (R5; FR-EVL-006). Offline."""

import re
import subprocess
import sys
from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError
from tests.evaluation.claim_support import ShownPassage
from tests.evaluation.code_state import REPO_ROOT
from tests.evaluation.reproducibility_labels import (
    GUIDE,
    PAPERS,
    Labels,
    ShownPaper,
    check_labels,
    render_sheet,
)

from app.services.reproducibility.checklist import CHECKLIST, CHECKLIST_VERSION

KEYS = [item.key for item in CHECKLIST]
HASH = "a" * 64


def labels(*rows: dict[str, str], **fields: Any) -> Labels:
    data: dict[str, Any] = {
        "labeller": "someone",
        "labelled_on": "2026-11-09",
        "guide_sha256": HASH,
        "checklist_version": CHECKLIST_VERSION,
        "labels": list(rows),
        **fields,
    }
    return Labels.model_validate(data)


def complete() -> list[dict[str, str]]:
    return [
        {"paper": paper, "item": key, "status": "reported"}
        for paper in PAPERS
        for key in KEYS
    ]


def paper(key: str = "p1", text: str = "A passage.") -> ShownPaper:
    return ShownPaper(key, f"Title of {key}", (ShownPassage(text, "Methods", 3),))


def sheet(*papers: ShownPaper) -> str:
    return render_sheet(
        papers or (paper("p1"), paper("p4"), paper("p5")),
        guide_sha256=HASH,
        today=date(2026, 11, 9),
    )


def test_three_papers_are_labelled_for_about_eighteen_items() -> None:
    assert len(PAPERS) == 3
    assert 15 <= len(PAPERS) * len(KEYS) <= 24


def test_complete_labels_are_accepted() -> None:
    check_labels(labels(*complete()), guide_sha256=HASH)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        pytest.param(lambda r: r[1:], "missing", id="missing"),
        pytest.param(lambda r: [*r, r[0]], "repeated", id="repeated"),
        pytest.param(
            lambda r: [*r, {"paper": "p1", "item": "other", "status": "reported"}],
            "unknown",
            id="unknown item",
        ),
    ],
)
def test_labels_must_cover_each_paper_and_item_once(change: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        check_labels(labels(*change(complete())), guide_sha256=HASH)


def test_labels_under_another_guide_are_refused() -> None:
    with pytest.raises(ValueError, match="guide"):
        check_labels(labels(*complete()), guide_sha256="b" * 64)


def test_labels_for_another_checklist_are_refused() -> None:
    with pytest.raises(ValueError, match="checklist"):
        check_labels(
            labels(*complete(), checklist_version="checklist-v0"), guide_sha256=HASH
        )


@pytest.mark.parametrize(
    "row",
    [
        pytest.param({"paper": "p1", "item": "x", "status": "good"}, id="status"),
        pytest.param({"paper": "p9", "item": "x", "status": "reported"}, id="paper"),
        pytest.param(
            {"paper": "p1", "item": "x", "status": "reported", "note": "y"}, id="extra"
        ),
    ],
)
def test_invalid_labels_are_refused(row: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        labels(row)


def test_every_paper_and_item_has_each_status_choice() -> None:
    page = sheet()

    for key in PAPERS:
        for item in KEYS:
            for status in (
                "reported",
                "partially_reported",
                "not_found",
                "needs_review",
            ):
                assert re.search(rf'name="{key}-{item}" value="{status}"', page), (
                    key,
                    item,
                    status,
                )


def test_the_sheet_shows_each_definition_and_the_location() -> None:
    page = sheet()

    for item in CHECKLIST:
        assert item.question in page
        assert item.reported in page
    assert "Methods" in page
    assert "page 3" in page


def test_an_unknown_location_is_shown_as_unknown() -> None:
    unknown = ShownPaper("p1", "T", (ShownPassage("Text.", None, None),))

    page = sheet(unknown)

    assert "section unknown" in page
    assert "page unknown" in page


def test_paper_text_and_titles_cannot_inject_markup() -> None:
    hostile = '<script>alert("x")</script>'
    bad = ShownPaper("p1", hostile, (ShownPassage(hostile, hostile, 1),))

    assert hostile not in sheet(bad)


def test_the_output_records_the_guide_and_checklist_version() -> None:
    page = sheet()

    assert HASH in page
    assert CHECKLIST_VERSION in page


def test_the_sheet_warns_that_not_found_is_no_verdict() -> None:
    assert "not found in the text shown" in sheet()


def test_the_guide_covers_every_status_and_points_to_the_checklist() -> None:
    guide = GUIDE.read_text(encoding="utf-8")

    for status in ("reported", "partially_reported", "not_found", "needs_review"):
        assert f"`{status}`" in guide
    assert CHECKLIST_VERSION in guide


def test_the_command_starts_outside_pytest() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "tests.evaluation.reproducibility_labels", "--help"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

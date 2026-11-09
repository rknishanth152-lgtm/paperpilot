"""Drawing, showing and scoring the claim-support sample (P6-T3, FR-EVL-004)."""

import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from tests.evaluation.claim_support import (
    Label,
    Labels,
    Sample,
    SampleCitation,
    SampleItem,
    ShownPassage,
    check_labels,
    claim_support_record,
    claim_support_result,
    draw_items,
    normalised_sha256,
    render_sheet,
    write_new,
)
from tests.evaluation.code_state import CodeState

STATE = CodeState(revision="abcdef1234567", clean=True)
RUN_AT = datetime(2026, 11, 9, 8, 30, 5, tzinfo=UTC)
PASSAGE = uuid.uuid4()


def citation(quote: str | None = "a quote") -> dict[str, Any]:
    return {
        "alias": "P1",
        "quote": quote,
        "valid": True,
        "reason": None,
        "passage_id": str(PASSAGE),
    }


def row(question_id: str, *texts: str) -> dict[str, Any]:
    return {
        "id": question_id,
        "question": f"Question {question_id}?",
        "error": None,
        "evidence_sufficiency": "sufficient",
        "statements": [
            {"text": text, "citations": [citation()], "has_valid_citation": True}
            for text in texts
        ],
    }


ROWS = [row("q01", "one", "two"), row("q02"), row("q03", "three")]


def item(name: str, statement: str = "A claim.") -> SampleItem:
    return SampleItem(
        item=name,
        question_id="q01",
        statement_index=0,
        question="What happened?",
        statement=statement,
        citations=(SampleCitation(alias="P1", quote="q", passage_id=PASSAGE),),
    )


def sample(*items: SampleItem) -> Sample:
    return Sample(
        version=1,
        seed=7,
        guide_sha256="c" * 64,
        source={"file": "answers.json", "sha256": "d" * 64},
        statements_in_source=len(items),
        items=items,
    )


TWO = sample(item("S01"), item("S02"))


def labels(*values: tuple[str, str, str], **fields: Any) -> Labels:
    data: dict[str, Any] = {
        "labeller": "someone",
        "labelled_on": "2026-11-09",
        "guide_sha256": "c" * 64,
        "labels": [
            {"item": i, "claim_support": c, "answers_question": a} for i, c, a in values
        ],
        **fields,
    }
    return Labels.model_validate(data)


GOOD = labels(("S01", "supported", "yes"), ("S02", "supported", "no"))


def test_every_statement_in_the_run_is_drawn() -> None:
    items = draw_items(ROWS, seed=7)

    assert sorted(i.statement for i in items) == ["one", "three", "two"]
    assert [i.item for i in items] == ["S01", "S02", "S03"]


def test_an_item_records_where_its_statement_came_from() -> None:
    drawn = {i.statement: i for i in draw_items(ROWS, seed=7)}

    assert (drawn["two"].question_id, drawn["two"].statement_index) == ("q01", 1)
    assert drawn["two"].question == "Question q01?"
    assert drawn["two"].citations[0].passage_id == PASSAGE


def test_the_draw_is_repeatable_and_depends_on_the_seed() -> None:
    many = [row(f"q{n}", f"s{n}") for n in range(30)]

    first = [i.statement for i in draw_items(many, seed=7)]

    assert first == [i.statement for i in draw_items(many, seed=7)]
    assert first != [i.statement for i in draw_items(many, seed=8)]
    assert first != [f"s{n}" for n in range(30)]


def test_a_citation_without_a_passage_cannot_be_labelled() -> None:
    broken = row("q01", "one")
    broken["statements"][0]["citations"][0]["passage_id"] = None

    with pytest.raises(ValueError, match="q01"):
        draw_items([broken], seed=7)


def test_a_model_error_row_contributes_nothing() -> None:
    assert draw_items([{"id": "q09", "question": "?", "error": "x"}], seed=7) == ()


def test_the_sample_does_not_carry_the_models_own_labels() -> None:
    text = sample(*draw_items(ROWS, seed=7)).model_dump_json()

    assert "evidence_sufficiency" not in text
    assert "sufficient" not in text
    assert "validated" not in text


def shown(text: str = "The passage.") -> dict[uuid.UUID, ShownPassage]:
    return {PASSAGE: ShownPassage(text=text, section="2 Methods", page=4)}


def test_the_sheet_shows_each_item_with_both_questions() -> None:
    page = render_sheet(TWO, shown(), today=date(2026, 11, 9))

    assert "What happened?" in page
    assert "A claim." in page
    assert "The passage." in page
    assert "2 Methods" in page
    assert "page 4" in page
    for name in ("S01", "S02"):
        assert f'name="{name}-claim_support"' in page
        assert f'name="{name}-answers_question"' in page
    for value in ("supported", "partly_supported", "not_supported", "cannot_judge"):
        assert f'value="{value}"' in page
    for value in ('value="yes"', 'value="partly"', 'value="no"'):
        assert value in page
    assert "c" * 64 in page
    assert 'value="2026-11-09"' in page


def test_an_unknown_page_or_section_is_shown_as_unknown() -> None:
    passages = {PASSAGE: ShownPassage(text="T", section=None, page=None)}

    assert "section unknown" in render_sheet(TWO, passages, today=date(2026, 11, 9))
    assert "page unknown" in render_sheet(TWO, passages, today=date(2026, 11, 9))


def test_paper_text_cannot_inject_markup_into_the_sheet() -> None:
    hostile = "<script>alert(1)</script>"
    page = render_sheet(
        sample(item("S01", statement=hostile)), shown(hostile), today=date(2026, 11, 9)
    )

    assert hostile not in page
    assert "&lt;script&gt;" in page


def test_a_question_and_section_cannot_inject_markup_either() -> None:
    hostile = "<img src=x>"
    base = item("S01")
    page = render_sheet(
        sample(base.model_copy(update={"question": hostile})),
        {PASSAGE: ShownPassage(text="T", section=hostile, page=1)},
        today=date(2026, 11, 9),
    )

    assert hostile not in page
    assert page.count("&lt;img src=x&gt;") == 2


def test_a_missing_passage_stops_the_sheet() -> None:
    with pytest.raises(KeyError):
        render_sheet(TWO, {}, today=date(2026, 11, 9))


def test_complete_labels_are_accepted() -> None:
    check_labels(TWO, GOOD, guide_sha256="c" * 64)


@pytest.mark.parametrize(
    ("given", "message"),
    [
        (labels(("S01", "supported", "yes")), "S02"),
        (
            labels(
                ("S01", "supported", "yes"),
                ("S02", "supported", "yes"),
                ("S03", "supported", "yes"),
            ),
            "S03",
        ),
        (
            labels(
                ("S01", "supported", "yes"),
                ("S01", "supported", "yes"),
                ("S02", "supported", "yes"),
            ),
            "S01",
        ),
    ],
)
def test_labels_must_cover_each_item_exactly_once(given: Labels, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        check_labels(TWO, given, guide_sha256="c" * 64)


def test_labels_made_under_another_guide_are_refused() -> None:
    other = labels(
        ("S01", "supported", "yes"), ("S02", "supported", "yes"), guide_sha256="e" * 64
    )

    with pytest.raises(ValueError, match="guide"):
        check_labels(TWO, other, guide_sha256="c" * 64)


def test_a_sample_drawn_under_another_guide_is_refused() -> None:
    other = labels(
        ("S01", "supported", "yes"), ("S02", "supported", "yes"), guide_sha256="e" * 64
    )

    with pytest.raises(ValueError, match="guide"):
        check_labels(TWO, other, guide_sha256="e" * 64)


@pytest.mark.parametrize(
    "bad",
    [
        {"claim_support": "maybe"},
        {"answers_question": "perhaps"},
        {"extra": "field"},
    ],
)
def test_a_label_outside_the_guide_is_refused(bad: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        Label.model_validate(
            {
                "item": "S01",
                "claim_support": "supported",
                "answers_question": "yes",
                **bad,
            }
        )


@pytest.mark.parametrize("name", ["", "   "])
def test_a_labeller_is_required(name: str) -> None:
    with pytest.raises(ValidationError):
        labels(("S01", "supported", "yes"), labeller=name)


def test_the_rate_is_supported_over_all_labelled() -> None:
    mixed = sample(item("S01"), item("S02"), item("S03"), item("S04"), item("S05"))
    given = labels(
        ("S01", "supported", "yes"),
        ("S02", "supported", "no"),
        ("S03", "partly_supported", "partly"),
        ("S04", "not_supported", "yes"),
        ("S05", "cannot_judge", "cannot_judge"),
    )

    result = claim_support_result(mixed, given)

    assert result["sample_size"] == 5
    assert result["claim_support"] == {
        "counts": {
            "supported": 2,
            "partly_supported": 1,
            "not_supported": 1,
            "cannot_judge": 1,
        },
        "rate": 0.4,
    }
    assert result["answers_question"] == {
        "counts": {"yes": 2, "partly": 1, "no": 1, "cannot_judge": 1},
        "rate": 0.4,
    }
    assert result["supported_but_not_fully_answering"] == 1


def test_a_supported_statement_answering_only_partly_is_counted() -> None:
    given = labels(("S01", "supported", "partly"), ("S02", "supported", "yes"))

    assert claim_support_result(TWO, given)["supported_but_not_fully_answering"] == 1


def record() -> dict[str, Any]:
    return claim_support_record(
        sample=TWO,
        labels=GOOD,
        sample_sha256="1" * 64,
        labels_sha256="2" * 64,
        state=STATE,
        run_at=RUN_AT,
    )


def test_a_saved_report_says_who_labelled_what() -> None:
    saved = record()

    assert saved["kind"] == "claim support, human labels"
    assert saved["labeller"] == "someone"
    assert saved["labelled_on"] == "2026-11-09"
    assert saved["sample_size"] == 2
    assert saved["guide_sha256"] == "c" * 64
    assert saved["sample_sha256"] == "1" * 64
    assert saved["labels_sha256"] == "2" * 64
    assert saved["source"] == TWO.source
    assert saved["seed"] == 7
    assert saved["code_revision"] == STATE.revision
    assert saved["working_tree_clean"] is True
    assert saved["run_at"] == "2026-11-09T08:30:05+00:00"
    assert saved["result"] == claim_support_result(TWO, GOOD)
    assert "one labeller" in saved["limits"]


def test_a_new_file_never_replaces_an_old_one(tmp_path: Path) -> None:
    path = tmp_path / "a.json"

    write_new({"a": 1}, path)

    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}
    with pytest.raises(FileExistsError):
        write_new({"a": 2}, path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}


def test_line_endings_do_not_change_a_files_identity(tmp_path: Path) -> None:
    unix = tmp_path / "u.md"
    windows = tmp_path / "w.md"
    unix.write_bytes(b"one\ntwo\n")
    windows.write_bytes(b"one\r\ntwo\r\n")

    assert normalised_sha256(unix) == normalised_sha256(windows)


def test_different_content_has_a_different_identity(tmp_path: Path) -> None:
    first = tmp_path / "a.md"
    second = tmp_path / "b.md"
    first.write_bytes(b"one\n")
    second.write_bytes(b"two\n")

    assert normalised_sha256(first) != normalised_sha256(second)

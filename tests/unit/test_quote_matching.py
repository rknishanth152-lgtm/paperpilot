"""Matching a model's quote against stored passage text (P5-T6; FR-CIT-002, OQ-013). Offline."""

import pytest

from app.services.answering.quotes import quote_in_passage

PASSAGE = (
    "The high rate of nonreplication (lack of confi rmation) is a consequence "
    "of claiming conclusive research fi ndings at p < 0.05, with 12 of 15 "
    "replications successful for BERT BASE (Dai and Le, 2015;Peters et al., 2018)."
)


@pytest.mark.parametrize(
    "quote",
    [
        pytest.param("is a consequence of claiming", id="exact"),
        pytest.param("lack of confi rmation", id="exact with split ligature"),
        pytest.param("lack of confirmation", id="model repaired the split"),
        pytest.param("lack of conﬁrmation", id="ligature character"),
        pytest.param("research findings at p", id="repaired at a word start"),
        pytest.param("is  a\nconsequence\tof", id="whitespace differs"),
        pytest.param("BERTBASE", id="space differs inside a name"),
        pytest.param("2015; Peters et al.", id="space added after punctuation"),
        pytest.param("(lack of", id="brackets kept"),
        pytest.param("12 of 15 replications", id="numbers kept"),
    ],
)
def test_true_quotes_are_accepted(quote: str) -> None:
    assert quote_in_passage(quote, PASSAGE)


@pytest.mark.parametrize(
    ("quote", "passage"),
    [
        pytest.param("a–b and c—d", "a-b and c-d", id="dashes in the quote"),
        pytest.param("a-b", "a–b", id="dash in the passage"),
        pytest.param("x − y", "x - y", id="minus sign"),
        pytest.param("“quoted”", '"quoted"', id="curly double quotes"),
        pytest.param("it's", "it’s", id="curly apostrophe"),
    ],
)
def test_typography_is_folded_on_both_sides(quote: str, passage: str) -> None:
    assert quote_in_passage(quote, passage)


@pytest.mark.parametrize(
    "quote",
    [
        pytest.param("with 13 of 15 replications", id="number changed"),
        pytest.param("is a result of claiming", id="word replaced"),
        pytest.param("is a of claiming", id="word dropped"),
        pytest.param("is not a consequence", id="not inserted"),
        pytest.param("Is A Consequence", id="case changed"),
        pytest.param("p > 0.05", id="comparison reversed"),
        pytest.param(
            "a sentence from somewhere else entirely", id="not in the passage"
        ),
        pytest.param("claiming a consequence", id="words reordered"),
        pytest.param(PASSAGE + " And more.", id="longer than the passage"),
    ],
)
def test_altered_quotes_are_rejected(quote: str) -> None:
    assert not quote_in_passage(quote, PASSAGE)


@pytest.mark.parametrize("quote", ["", "   ", "\n\t"])
def test_an_empty_quote_is_never_found(quote: str) -> None:
    assert not quote_in_passage(quote, PASSAGE)


def test_known_limit_differences_only_in_spacing_are_not_detected() -> None:
    """Recorded in progress.md §6.14: rare, and this check never proves support."""
    assert quote_in_passage("notable", "They were not able to repeat it.")

"""Tests for DOI normalisation (P2-T4, FR-ING-008, FR-DIS-002)."""

import pytest

from app.services.doi import normalize_doi

# DOIs of the Phase 1 papers, as GROBID returned them and as checked on the
# publishers' pages (docs/experiments/grobid-feasibility.md §3).
REAL_DOIS = [
    ("10.7554/eLife.71601", "10.7554/elife.71601"),
    ("10.1371/journal.pmed.0020124", "10.1371/journal.pmed.0020124"),
    ("10.1371/journal.pone.0000308", "10.1371/journal.pone.0000308"),
    ("10.1371/journal.pone.0024357", "10.1371/journal.pone.0024357"),
]


@pytest.mark.parametrize(("raw", "expected"), REAL_DOIS)
def test_real_dois_from_the_experiment(raw: str, expected: str) -> None:
    assert normalize_doi(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "10.1371/journal.pone.0000308",
        "10.1371/JOURNAL.PONE.0000308",
        "  10.1371/journal.pone.0000308\n",
        "doi:10.1371/journal.pone.0000308",
        "DOI: 10.1371/journal.pone.0000308",
        "https://doi.org/10.1371/journal.pone.0000308",
        "http://doi.org/10.1371/journal.pone.0000308",
        "HTTPS://DOI.ORG/10.1371/journal.pone.0000308",
        "https://dx.doi.org/10.1371/journal.pone.0000308",
        "http://dx.doi.org/10.1371/journal.pone.0000308",
        "doi.org/10.1371/journal.pone.0000308",
        "dx.doi.org/10.1371/journal.pone.0000308",
    ],
)
def test_textual_variants_of_one_doi_match(raw: str) -> None:
    assert normalize_doi(raw) == "10.1371/journal.pone.0000308"


def test_suffix_may_contain_slashes_and_punctuation() -> None:
    assert (
        normalize_doi("10.1002/(SICI)1097-4636(199703)")
        == "10.1002/(sici)1097-4636(199703)"
    )


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "doi:",
        "https://doi.org/",
        "not a doi",
        "11.1371/journal.pone.0000308",  # must start with 10.
        "10.137/journal.pone.0000308",  # registrant code has 4-9 digits
        "10.1371",  # no suffix
        "10.1371/",  # empty suffix
        "10.1371/journal. pone.0000308",  # a DOI never contains whitespace
        "https://example.org/10.1371/journal.pone.0000308",  # not a DOI resolver
    ],
)
def test_values_that_are_not_dois_give_none(raw: str | None) -> None:
    assert normalize_doi(raw) is None


def test_result_satisfies_the_database_check() -> None:
    # papers.doi_normalized has CHECK (doi_normalized LIKE '10.%').
    normalized = normalize_doi("https://doi.org/10.7554/eLife.71601")
    assert normalized is not None
    assert normalized.startswith("10.")


def test_normalising_twice_changes_nothing() -> None:
    once = normalize_doi("DOI: 10.7554/eLife.71601")
    assert once is not None
    assert normalize_doi(once) == once

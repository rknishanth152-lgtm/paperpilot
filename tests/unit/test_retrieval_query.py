"""Cleaning a question before it reaches the database (P4-T3, FR-RET-003)."""

import pytest

from app.config import Settings
from app.services.retrieval.keyword import QueryTooLongError, clean_question


@pytest.mark.parametrize(
    ("raw", "cleaned"),
    [
        ("plain question", "plain question"),
        ("a\x00b", "a b"),
        ("a\ud800b", "ab"),
        ("\x00", " "),
        ("", ""),
        ("résumé β-catenin 中文", "résumé β-catenin 中文"),
    ],
)
def test_clean_question(raw: str, cleaned: str) -> None:
    assert clean_question(raw, max_chars=100) == cleaned


def test_limit_is_inclusive() -> None:
    assert clean_question("x" * 10, max_chars=10) == "x" * 10

    with pytest.raises(QueryTooLongError) as caught:
        clean_question("x" * 11, max_chars=10)

    assert caught.value.max_chars == 10
    assert "10" in caught.value.message
    assert "xxx" not in caught.value.message  # the question is not repeated


def test_query_limit_setting_has_a_default_and_must_be_positive() -> None:
    assert Settings(_env_file=None, postgres_password="pw").max_query_chars == 2000

    with pytest.raises(ValueError, match="max_query_chars"):
        Settings(_env_file=None, postgres_password="pw", max_query_chars=0)

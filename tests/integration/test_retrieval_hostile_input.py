"""Retrieval with hostile input, and scope isolation (P4-T4; FR-RET-002, FR-RET-003).

The question is data: it must never raise, never act as an operator, never
change stored data, and never reach outside the requested scope.
"""

import random
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.test_keyword_retrieval import (
    MAX_CHARS,
    add_document,
    add_paper,
    search,
    texts,
)

from app.models import Document, Paper, Passage

GLACIERS = "Glaciers retreated quickly."
VOLCANOES = "Volcanoes erupted again."


def snapshot(sessions: sessionmaker[Session]) -> tuple[int, int, int, list[str]]:
    with sessions() as session:
        return (
            session.scalar(select(func.count()).select_from(Paper)) or 0,
            session.scalar(select(func.count()).select_from(Document)) or 0,
            session.scalar(select(func.count()).select_from(Passage)) or 0,
            list(session.scalars(select(Passage.text).order_by(Passage.id))),
        )


# --- Questions with no searchable words --------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "",
        " ",
        "\n\t  ",
        "?!...;:--()",
        "the of and is",
        "\x00",
        "\ud800",
        "-",
        "'",
        '"',
        "&",
        "|",
        "!",
        "()",
        ":*",
        "<->",
    ],
)
def test_nothing_searchable_gives_an_empty_list(
    sessions: sessionmaker[Session], question: str
) -> None:
    add_document(sessions, GLACIERS)

    assert search(sessions, question) == []


# --- SQL-like input -----------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "'; DROP TABLE passages; --",
        '"; DELETE FROM documents; --',
        "x'); TRUNCATE passages, documents, papers; --",
        "1; SELECT pg_sleep(5)",
        "' UNION SELECT text FROM passages --",
        "$1 %s %(q)s {} :q",
        "E'\\x27' ::tsquery",
    ],
)
def test_sql_like_input_changes_nothing(
    sessions: sessionmaker[Session], question: str
) -> None:
    add_document(sessions, GLACIERS, VOLCANOES)
    before = snapshot(sessions)

    assert search(sessions, question) == []
    assert snapshot(sessions) == before


def test_always_true_condition_does_not_match_everything(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, GLACIERS, VOLCANOES)

    assert search(sessions, "' OR '1'='1") == []


def test_real_words_inside_sql_like_input_are_still_searched(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, GLACIERS, VOLCANOES)
    before = snapshot(sessions)

    assert texts(search(sessions, "glacier'); DROP TABLE passages; --")) == [GLACIERS]
    assert snapshot(sessions) == before


# --- Operator-like input is not obeyed ----------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "glacier & !retreat",  # NOT is not honoured
        "!retreat",
        "-retreat",
        "glacier -retreat",
        '"glacier quickly"',  # not a phrase: the words are not adjacent
        "glacier <-> quickly",
        "glacier:A",
        "(glacier",
        "glacier)",
        "glacier AND",
        "glacier NOT quickly",
    ],
)
def test_operators_in_the_question_have_no_effect(
    sessions: sessionmaker[Session], question: str
) -> None:
    add_document(sessions, GLACIERS, VOLCANOES)

    assert texts(search(sessions, question)) == [GLACIERS]


def test_prefix_syntax_does_not_widen_the_match(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, GLACIERS)

    assert search(sessions, "glac:*") == []


# --- Awkward tokens survive the conversion to OR -------------------------------


@pytest.mark.parametrize(
    "token",
    [
        "O'Brien's",
        "http://example.org/x?a=1&b=2",
        "a.b@example.org",
        "/usr/lib/x.so",
        "C:\\temp\\file",
        "v1.2.3",
        "3.14",
        "p-value",
        "β-catenin",
        "x|y",
    ],
)
def test_a_passage_can_be_found_by_its_own_awkward_token(
    sessions: sessionmaker[Session], token: str
) -> None:
    body = f"Reported {token} here."
    add_document(sessions, body, VOLCANOES)

    assert texts(search(sessions, token)) == [body]


def test_ampersand_inside_a_token_is_not_treated_as_a_separator(
    sessions: sessionmaker[Session],
) -> None:
    """Only the path `/x?a=1&b=2` is shared, so it must survive the conversion."""
    body = "See http://example.org/x?a=1&b=2 here."
    add_document(sessions, body)

    assert texts(search(sessions, "http://other.org/x?a=1&b=2")) == [body]


@pytest.mark.parametrize(("term", "question"), [("AT&T", "AT&T"), ("vitamin A", "A")])
def test_known_limit_stop_words_are_not_searchable(
    sessions: sessionmaker[Session], term: str, question: str
) -> None:
    """A limit of the `english` configuration, recorded in retrieval.md §3.

    `AT`, `T` and `A` are stop words, so these terms reduce to little or
    nothing. If this starts failing, the configuration has changed.
    """
    add_document(sessions, f"Reported {term} here.")

    assert search(sessions, question) == []


# --- Arbitrary input ----------------------------------------------------------

_PIECES = [
    "'", '"', "\\", "&", "|", "!", "(", ")", ":", "*", "<->", "<2>", "-", "--", ";",
    "%", "_", "\x00", "\ud800", "é", "😀", "中文", "OR", "AND", "NOT", "glacier",
    "volcano", "the", " ", "\n", "\t", "$1", "%s", "{}", "E'", "::tsquery", "/*", "*/",
]  # fmt: skip


def test_arbitrary_input_never_raises_or_leaves_the_scope(
    sessions: sessionmaker[Session],
) -> None:
    wanted = add_document(sessions, GLACIERS, VOLCANOES)
    add_document(sessions, GLACIERS, VOLCANOES)
    before = snapshot(sessions)
    rng = random.Random(20261108)

    for _ in range(300):
        question = "".join(rng.choices(_PIECES, k=rng.randint(0, 40)))
        results = search(sessions, question, k=3, document_ids=[wanted])
        assert len(results) <= 3
        assert all(result.document_id == wanted for result in results)

    assert snapshot(sessions) == before


def test_question_at_the_limit_made_of_operators_works(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, GLACIERS)

    assert search(sessions, "a&b|" * (MAX_CHARS // 4)) == []


# --- Scope isolation ----------------------------------------------------------


def test_stronger_matches_outside_the_scope_never_appear_or_use_up_k(
    sessions: sessionmaker[Session],
) -> None:
    add_document(sessions, *["Glacier glacier glacier glacier."] * 6)
    wanted = add_document(sessions, "A glacier once, in many other words of text.")

    results = search(sessions, "glacier", k=1, document_ids=[wanted])

    assert [result.document_id for result in results] == [wanted]


def test_paper_scope_excludes_other_papers(sessions: sessionmaker[Session]) -> None:
    paper = add_paper(sessions)
    other = add_paper(sessions)
    add_document(sessions, *["Glacier glacier glacier."] * 6, paper_id=other)
    add_document(sessions, "A glacier once, in other words.", paper_id=paper)

    results = search(sessions, "glacier", k=5, paper_ids=[paper])

    assert [result.paper_id for result in results] == [paper]


def test_naming_an_unparsed_document_does_not_expose_it(
    sessions: sessionmaker[Session],
) -> None:
    parsed = add_document(sessions, GLACIERS)
    failed = add_document(sessions, GLACIERS, status="failed")

    results = search(sessions, "glacier", document_ids=[parsed, failed])

    assert [result.document_id for result in results] == [parsed]


def test_scope_on_a_document_from_another_paper_gives_nothing(
    sessions: sessionmaker[Session],
) -> None:
    paper = add_paper(sessions)
    document = add_document(sessions, GLACIERS)

    assert search(sessions, "glacier", document_ids=[document], paper_ids=[paper]) == []


def test_several_scoped_documents_are_all_searched(
    sessions: sessionmaker[Session],
) -> None:
    first = add_document(sessions, GLACIERS)
    second = add_document(sessions, GLACIERS)
    add_document(sessions, GLACIERS)

    results = search(sessions, "glacier", document_ids=[first, second])

    assert {result.document_id for result in results} == {first, second}


# --- Deterministic order ------------------------------------------------------


def test_order_is_identical_across_repeated_searches_and_documents(
    sessions: sessionmaker[Session],
) -> None:
    for _ in range(4):
        add_document(sessions, *[GLACIERS] * 3)

    first = [r.passage_id for r in search(sessions, "glacier", k=12)]

    assert len(first) == 12
    assert first == sorted(first, key=lambda value: uuid.UUID(str(value)))
    for _ in range(20):
        assert [r.passage_id for r in search(sessions, "glacier", k=12)] == first

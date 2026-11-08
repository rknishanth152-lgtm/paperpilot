"""The deterministic citation validator (P5-T7; FR-CIT-001, -002, -004). Offline."""

import uuid
from typing import Any

import pytest

from app.schemas.answer import Citation, ModelAnswer, Statement
from app.services.answering.citations import AnswerScope, validate_answer
from app.services.answering.context import AnswerContext
from app.services.retrieval.keyword import RetrievedPassage

PAPER, OTHER_PAPER = uuid.uuid4(), uuid.uuid4()
DOCUMENT, OTHER_DOCUMENT = uuid.uuid4(), uuid.uuid4()
BODY = "Glaciers retreated quickly in the last decade."
NO_SCOPE = AnswerScope()


def passage(**values: Any) -> RetrievedPassage:
    fields: dict[str, Any] = {
        "passage_id": uuid.uuid4(),
        "document_id": DOCUMENT,
        "paper_id": PAPER,
        "section": None,
        "page_start": None,
        "page_end": None,
        "text": BODY,
        "score": 0.5,
        **values,
    }
    return RetrievedPassage(**fields)


SHOWN = passage()
DROPPED = passage(text="A passage the model was not shown.")
ELSEWHERE = passage(paper_id=OTHER_PAPER, document_id=OTHER_DOCUMENT)
CONTEXT = AnswerContext(
    user_message="{}",
    aliases={"P1": SHOWN, "P2": ELSEWHERE},
    dropped={"P3": DROPPED},
)


def cite(alias: str = "P1", quote: str | None = None) -> Citation:
    return Citation(alias=alias, quote=quote)


def said(*citations: Citation, text: str = "A claim.") -> Statement:
    return Statement(text=text, citations=citations)


def answer(
    *statements: Statement,
    sufficiency: str = "sufficient",
    limitations: str | None = None,
) -> ModelAnswer:
    fields: dict[str, Any] = {
        "statements": statements,
        "evidence_sufficiency": sufficiency,
        "limitations": limitations,
    }
    return ModelAnswer(**fields)


def check(citation: Citation, scope: AnswerScope = NO_SCOPE) -> Any:
    return (
        validate_answer(answer(said(citation)), CONTEXT, scope)
        .statements[0]
        .citations[0]
    )


# --- One citation -------------------------------------------------------------


def test_a_real_citation_is_valid_and_resolved() -> None:
    result = check(cite("P1"))

    assert (result.valid, result.reason) == (True, None)
    assert result.alias == "P1"
    assert result.passage == SHOWN


def test_an_unknown_alias_is_passage_not_found() -> None:
    result = check(cite("P99"))

    assert (result.valid, result.reason) == (False, "passage_not_found")
    assert result.passage is None


@pytest.mark.parametrize("alias", ["p1", " P1", "P1 ", "", "1", str(SHOWN.passage_id)])
def test_aliases_must_match_exactly(alias: str) -> None:
    """A database id from the model is not accepted either (AD-007)."""
    assert check(cite(alias)).reason == "passage_not_found"


def test_a_passage_the_model_was_not_shown_is_not_in_context() -> None:
    result = check(cite("P3"))

    assert (result.valid, result.reason) == (False, "not_in_context")
    assert result.passage == DROPPED


def test_a_passage_from_a_paper_outside_the_scope_is_wrong_paper() -> None:
    result = check(cite("P2"), AnswerScope(paper_ids=frozenset({PAPER})))

    assert (result.valid, result.reason) == (False, "wrong_paper")
    assert result.passage == ELSEWHERE


def test_a_passage_from_a_document_outside_the_scope_is_wrong_paper() -> None:
    assert (
        check(cite("P2"), AnswerScope(document_ids=frozenset({DOCUMENT}))).reason
        == "wrong_paper"
    )


def test_both_scopes_must_hold() -> None:
    scope = AnswerScope(
        document_ids=frozenset({DOCUMENT, OTHER_DOCUMENT}), paper_ids=frozenset({PAPER})
    )

    assert check(cite("P1"), scope).valid
    assert check(cite("P2"), scope).reason == "wrong_paper"


def test_no_scope_means_no_restriction() -> None:
    assert check(cite("P2")).valid


def test_an_empty_scope_allows_nothing() -> None:
    assert check(cite("P1"), AnswerScope(paper_ids=frozenset())).reason == "wrong_paper"


def test_a_quote_found_in_the_passage_is_valid() -> None:
    assert check(cite("P1", quote="retreated quickly")).valid


def test_an_altered_quote_is_quote_mismatch() -> None:
    result = check(cite("P1", quote="retreated slowly"))

    assert (result.valid, result.reason) == (False, "quote_mismatch")
    assert result.quote == "retreated slowly"


def test_a_quote_from_another_passage_is_quote_mismatch() -> None:
    assert check(cite("P1", quote="A passage the model")).reason == "quote_mismatch"


def test_a_citation_without_a_quote_needs_no_quote_check() -> None:
    assert check(cite("P1", quote=None)).valid


def test_scope_is_reported_before_the_quote() -> None:
    result = check(
        cite("P2", quote="not in that passage"),
        AnswerScope(paper_ids=frozenset({PAPER})),
    )

    assert result.reason == "wrong_paper"


# --- The whole answer (FR-CIT-004) --------------------------------------------


def status(*statements: Statement, sufficiency: str = "sufficient") -> str:
    return validate_answer(
        answer(*statements, sufficiency=sufficiency), CONTEXT, NO_SCOPE
    ).validation_status


def test_all_valid_citations_validate_the_answer() -> None:
    assert (
        status(said(cite("P1")), said(cite("P2"), cite("P1", "Glaciers")))
        == "validated"
    )


@pytest.mark.parametrize("sufficiency", ["sufficient", "partial"])
def test_one_invalid_citation_fails_the_whole_answer(sufficiency: str) -> None:
    assert (
        status(said(cite("P1")), said(cite("P99")), sufficiency=sufficiency) == "failed"
    )


def test_an_invalid_citation_beside_a_valid_one_still_fails() -> None:
    assert status(said(cite("P1"), cite("P99"))) == "failed"


@pytest.mark.parametrize("sufficiency", ["sufficient", "partial"])
def test_a_statement_with_no_citation_fails_the_answer(sufficiency: str) -> None:
    assert status(said(cite("P1")), said(), sufficiency=sufficiency) == "failed"


def test_an_insufficient_answer_with_no_statements_is_validated() -> None:
    result = validate_answer(
        answer(sufficiency="insufficient", limitations="Not covered."),
        CONTEXT,
        NO_SCOPE,
    )

    assert result.validation_status == "validated"
    assert result.evidence_sufficiency == "insufficient"
    assert result.statements == ()
    assert result.limitations == "Not covered."


def test_statements_report_whether_they_have_a_valid_citation() -> None:
    result = validate_answer(
        answer(said(cite("P1")), said(cite("P99")), said()), CONTEXT, NO_SCOPE
    )

    assert [s.has_valid_citation for s in result.statements] == [True, False, False]


def test_the_answer_keeps_its_text_and_order() -> None:
    result = validate_answer(
        answer(
            said(cite("P1"), text="First."),
            said(cite("P2"), text="Second."),
            sufficiency="partial",
            limitations="Limited.",
        ),
        CONTEXT,
        NO_SCOPE,
    )

    assert [s.text for s in result.statements] == ["First.", "Second."]
    assert (result.evidence_sufficiency, result.limitations) == ("partial", "Limited.")


def test_a_failed_answer_reports_every_citation_not_just_the_first() -> None:
    result = validate_answer(
        answer(said(cite("P99"), cite("P3"), cite("P1", "never said"))),
        CONTEXT,
        NO_SCOPE,
    )

    assert [c.reason for c in result.statements[0].citations] == [
        "passage_not_found",
        "not_in_context",
        "quote_mismatch",
    ]

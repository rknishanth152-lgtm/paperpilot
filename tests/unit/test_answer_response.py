"""Assembling the final answer (P5-T9; FR-QA-006, FR-CIT-003, FR-CIT-005). Offline."""

import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.answer_response import AnswerResponse
from app.services.answering.citations import (
    CheckedCitation,
    CheckedStatement,
    ValidatedAnswer,
)
from app.services.answering.context import AnswerContext
from app.services.answering.response import assemble_response
from app.services.retrieval.keyword import RetrievedPassage

PAPER = uuid.uuid4()


def passage(**values: Any) -> RetrievedPassage:
    fields: dict[str, Any] = {
        "passage_id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "paper_id": PAPER,
        "section": "2 Methods",
        "page_start": 4,
        "page_end": 5,
        "text": "Stored   passage text.",
        "score": 0.5,
        **values,
    }
    return RetrievedPassage(**fields)


FIRST, SECOND, THIRD = (
    passage(),
    passage(section=None, page_start=None, page_end=None),
    passage(),
)
CONTEXT = AnswerContext(
    user_message="{}", aliases={"P1": FIRST, "P2": SECOND}, dropped={"P3": THIRD}
)


def good(alias: str = "P1", item: RetrievedPassage = FIRST) -> CheckedCitation:
    return CheckedCitation(alias, "a quote", item, None)


def statement(*citations: CheckedCitation, text: str = "A claim.") -> CheckedStatement:
    return CheckedStatement(text, citations, any(c.valid for c in citations))


def validated(*statements: CheckedStatement, **values: Any) -> ValidatedAnswer:
    fields: dict[str, Any] = {
        "statements": statements,
        "evidence_sufficiency": "sufficient",
        "limitations": None,
        "validation_status": "validated",
        **values,
    }
    return ValidatedAnswer(**fields)


def assemble(answer: ValidatedAnswer, **values: Any) -> AnswerResponse:
    fields: dict[str, Any] = {
        "context": CONTEXT,
        "model": "fake-model",
        "prompt_version": "answer-v1",
        "paper_titles": {PAPER: "A Paper"},
        **values,
    }
    return assemble_response(answer, **fields)


def test_answer_fields_are_carried_over() -> None:
    result = assemble(
        validated(
            statement(good(), text="The claim."),
            evidence_sufficiency="partial",
            limitations="Limited.",
        )
    )

    assert result.evidence_sufficiency == "partial"
    assert result.limitations == "Limited."
    assert result.validation_status == "validated"
    [only] = result.statements
    assert only.text == "The claim."
    assert only.has_valid_citation is True


def test_a_valid_citation_links_to_its_passage() -> None:
    [citation] = assemble(validated(statement(good()))).statements[0].citations

    assert (citation.alias, citation.quote) == ("P1", "a quote")
    assert (citation.valid, citation.reason) == (True, None)
    assert citation.passage_id == FIRST.passage_id


@pytest.mark.parametrize(
    "reason",
    ["not_in_context", "wrong_paper", "quote_mismatch"],
)
def test_an_invalid_citation_gives_its_reason_and_no_link(reason: Any) -> None:
    failed = CheckedCitation("P2", "q", SECOND, reason)

    [citation] = (
        assemble(validated(statement(failed), validation_status="failed"))
        .statements[0]
        .citations
    )

    assert (citation.valid, citation.reason) == (False, reason)
    assert citation.passage_id is None


def test_evidence_location_comes_from_the_stored_passage() -> None:
    [evidence] = assemble(validated(statement(good()))).evidence

    assert evidence.alias == "P1"
    assert evidence.passage_id == FIRST.passage_id
    assert evidence.document_id == FIRST.document_id
    assert evidence.paper_id == PAPER
    assert evidence.paper_title == "A Paper"
    assert evidence.section == "2 Methods"
    assert (evidence.page_start, evidence.page_end) == (4, 5)
    assert evidence.text == "Stored   passage text."


def test_unknown_page_and_section_stay_null() -> None:
    [evidence] = assemble(validated(statement(good("P2", SECOND)))).evidence

    assert (evidence.section, evidence.page_start, evidence.page_end) == (
        None,
        None,
        None,
    )


def test_a_paper_without_a_title_has_a_null_title() -> None:
    [evidence] = assemble(validated(statement(good())), paper_titles={}).evidence

    assert evidence.paper_title is None


def test_evidence_lists_each_cited_passage_once_in_citation_order() -> None:
    result = assemble(
        validated(
            statement(good("P2", SECOND), good("P1", FIRST)),
            statement(good("P1", FIRST)),
        )
    )

    assert [e.alias for e in result.evidence] == ["P2", "P1"]


def test_only_valid_citations_become_evidence() -> None:
    result = assemble(
        validated(
            statement(
                good("P1", FIRST),
                CheckedCitation("P2", "x", SECOND, "quote_mismatch"),
                CheckedCitation("P3", None, THIRD, "not_in_context"),
                CheckedCitation("P99", None, None, "passage_not_found"),
            ),
            validation_status="failed",
        )
    )

    assert [e.alias for e in result.evidence] == ["P1"]
    assert result.validation_status == "failed"


def test_retrieved_passages_are_reported_in_rank_order_including_dropped() -> None:
    result = assemble(validated(statement(good())))

    assert result.retrieved_passage_ids == (
        FIRST.passage_id,
        SECOND.passage_id,
        THIRD.passage_id,
    )
    assert result.passages_dropped == 1


def test_provenance_is_reported() -> None:
    result = assemble(validated(statement(good())), model="fake-x", prompt_version="v9")

    assert result.model == "fake-x"
    assert result.prompt_version == "v9"
    assert result.retrieval_method == "keyword_full_text"


def test_claim_support_is_always_not_evaluated() -> None:
    assert assemble(validated(statement(good()))).claim_support == "not_evaluated"

    with pytest.raises(ValidationError):
        AnswerResponse.model_validate(
            {
                **assemble(validated(statement(good()))).model_dump(),
                "claim_support": "supported",
            }
        )


def test_an_answer_with_no_model_call_reports_no_model() -> None:
    empty = AnswerContext(user_message="{}", aliases={}, dropped={})

    result = assemble(
        validated(evidence_sufficiency="insufficient", limitations="Nothing found."),
        context=empty,
        model=None,
        prompt_version=None,
    )

    assert (result.model, result.prompt_version) == (None, None)
    assert result.statements == ()
    assert result.evidence == ()
    assert result.retrieved_passage_ids == ()


def test_the_response_rejects_unknown_fields() -> None:
    data = assemble(validated(statement(good()))).model_dump()

    with pytest.raises(ValidationError):
        AnswerResponse.model_validate({**data, "confidence": 0.9})

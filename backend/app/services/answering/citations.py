"""The deterministic citation validator (P5-T7; FR-CIT-001, -002, -004, AD-008).

Each citation is checked in a fixed order, and the first failure is its reason:

1. `passage_not_found`: the alias matches no retrieved passage.
2. `not_in_context`: it was retrieved but dropped, so the model never saw it.
3. `wrong_paper`: the passage is outside the question's scope.
4. `quote_mismatch`: a quote was given and is not in the passage.

An answer is `validated` only if every citation is valid and every statement
has at least one. Anything else is `failed`, and every citation is reported.

This proves that a citation points to a real, in-scope passage containing any
quote. It does not prove that the passage supports the statement (AD-008).
"""

import uuid
from dataclasses import dataclass
from typing import Literal

from app.schemas.answer import Citation, ModelAnswer, Statement
from app.services.answering.context import AnswerContext
from app.services.answering.quotes import quote_in_passage
from app.services.retrieval.keyword import RetrievedPassage

CitationFailure = Literal[
    "passage_not_found", "not_in_context", "wrong_paper", "quote_mismatch"
]


@dataclass(frozen=True)
class AnswerScope:
    """`None` means no restriction by that field; empty means nothing is in scope."""

    document_ids: frozenset[uuid.UUID] | None = None
    paper_ids: frozenset[uuid.UUID] | None = None

    def allows(self, passage: RetrievedPassage) -> bool:
        return (
            self.document_ids is None or passage.document_id in self.document_ids
        ) and (self.paper_ids is None or passage.paper_id in self.paper_ids)


@dataclass(frozen=True)
class CheckedCitation:
    alias: str
    quote: str | None
    passage: RetrievedPassage | None  # None when the alias resolved to nothing
    reason: CitationFailure | None

    @property
    def valid(self) -> bool:
        return self.reason is None


@dataclass(frozen=True)
class CheckedStatement:
    text: str
    citations: tuple[CheckedCitation, ...]
    has_valid_citation: bool


@dataclass(frozen=True)
class ValidatedAnswer:
    statements: tuple[CheckedStatement, ...]
    evidence_sufficiency: Literal["sufficient", "partial", "insufficient"]
    limitations: str | None
    validation_status: Literal["validated", "failed"]


def _check_citation(
    citation: Citation, context: AnswerContext, scope: AnswerScope
) -> CheckedCitation:
    alias, quote = citation.alias, citation.quote
    if alias in context.dropped:
        return CheckedCitation(alias, quote, context.dropped[alias], "not_in_context")
    passage = context.aliases.get(alias)
    if passage is None:
        return CheckedCitation(alias, quote, None, "passage_not_found")
    if not scope.allows(passage):
        return CheckedCitation(alias, quote, passage, "wrong_paper")
    if quote is not None and not quote_in_passage(quote, passage.text):
        return CheckedCitation(alias, quote, passage, "quote_mismatch")
    return CheckedCitation(alias, quote, passage, None)


def _check_statement(
    statement: Statement, context: AnswerContext, scope: AnswerScope
) -> CheckedStatement:
    citations = tuple(_check_citation(c, context, scope) for c in statement.citations)
    return CheckedStatement(
        text=statement.text,
        citations=citations,
        has_valid_citation=any(citation.valid for citation in citations),
    )


def validate_answer(
    answer: ModelAnswer, context: AnswerContext, scope: AnswerScope
) -> ValidatedAnswer:
    statements = tuple(_check_statement(s, context, scope) for s in answer.statements)
    passed = all(
        statement.has_valid_citation
        and all(citation.valid for citation in statement.citations)
        for statement in statements
    )
    return ValidatedAnswer(
        statements=statements,
        evidence_sufficiency=answer.evidence_sufficiency,
        limitations=answer.limitations,
        validation_status="validated" if passed else "failed",
    )

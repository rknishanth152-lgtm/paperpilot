"""Turning a validated answer into the final response (P5-T9; FR-QA-006, FR-CIT-003).

Only passages behind a valid citation are presented as evidence, each once, in
the order first cited. Their locations come from the stored passage.
"""

import uuid
from collections.abc import Mapping

from app.schemas.answer_response import (
    AnswerResponse,
    CitationResponse,
    EvidencePassage,
    StatementResponse,
)
from app.services.answering.citations import CheckedCitation, ValidatedAnswer
from app.services.answering.context import AnswerContext
from app.services.retrieval.selection import KEYWORD_METHOD


def _citation(citation: CheckedCitation) -> CitationResponse:
    linked = citation.passage if citation.valid else None
    return CitationResponse(
        alias=citation.alias,
        quote=citation.quote,
        valid=citation.valid,
        reason=citation.reason,
        passage_id=linked.passage_id if linked else None,
    )


def _evidence(
    answer: ValidatedAnswer, paper_titles: Mapping[uuid.UUID, str | None]
) -> tuple[EvidencePassage, ...]:
    evidence: dict[uuid.UUID, EvidencePassage] = {}
    for statement in answer.statements:
        for citation in statement.citations:
            passage = citation.passage
            if citation.valid and passage and passage.passage_id not in evidence:
                evidence[passage.passage_id] = EvidencePassage(
                    alias=citation.alias,
                    passage_id=passage.passage_id,
                    document_id=passage.document_id,
                    paper_id=passage.paper_id,
                    paper_title=paper_titles.get(passage.paper_id),
                    section=passage.section,
                    page_start=passage.page_start,
                    page_end=passage.page_end,
                    text=passage.text,
                )
    return tuple(evidence.values())


def assemble_response(
    answer: ValidatedAnswer,
    *,
    context: AnswerContext,
    model: str | None,
    prompt_version: str | None,
    paper_titles: Mapping[uuid.UUID, str | None],
    retrieval_method: str = KEYWORD_METHOD,
) -> AnswerResponse:
    retrieved = [*context.aliases.values(), *context.dropped.values()]
    return AnswerResponse(
        statements=tuple(
            StatementResponse(
                text=statement.text,
                citations=tuple(_citation(c) for c in statement.citations),
                has_valid_citation=statement.has_valid_citation,
            )
            for statement in answer.statements
        ),
        evidence=_evidence(answer, paper_titles),
        evidence_sufficiency=answer.evidence_sufficiency,
        limitations=answer.limitations,
        validation_status=answer.validation_status,
        claim_support="not_evaluated",
        retrieved_passage_ids=tuple(passage.passage_id for passage in retrieved),
        passages_dropped=context.passages_dropped,
        retrieval_method=retrieval_method,
        model=model,
        prompt_version=prompt_version,
    )

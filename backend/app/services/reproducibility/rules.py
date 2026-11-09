"""What each checklist status needs. Pure functions (R6; FR-REP-002, FR-REP-003).

`reported` and `partially_reported` stand only if every quote given is verified
in the passage it cites. Otherwise the status becomes `needs_review`, and the
model's explanation is dropped because it argued for the status just refused.

A verified quote shows the words are in the passage. It does not show that the
passage meets the item's definition (AD-008).
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field

from app.schemas.assessment import ModelAssessment
from app.services.answering.quotes import quote_in_passage
from app.services.retrieval.keyword import RetrievedPassage

EVIDENCE_REQUIRED = ("reported", "partially_reported")


@dataclass(frozen=True)
class Decision:
    status: str
    review_reason: str | None
    explanation: str | None
    quotes: Mapping[uuid.UUID, str] = field(default_factory=dict)


def _verified_quotes(
    output: ModelAssessment, shown: Mapping[str, RetrievedPassage]
) -> dict[uuid.UUID, str] | None:
    """Quotes by passage, first per passage, or None unless all are verified."""
    quotes: dict[uuid.UUID, str] = {}
    for evidence in output.evidence:
        passage = shown.get(evidence.alias)
        if passage is None or not quote_in_passage(evidence.quote, passage.text):
            return None
        quotes.setdefault(passage.passage_id, evidence.quote)
    return quotes or None


def decide(output: ModelAssessment, shown: Mapping[str, RetrievedPassage]) -> Decision:
    """The status to store for the model's output on the passages it was shown."""
    if output.status == "needs_review":
        return Decision("needs_review", "model_uncertain", output.explanation)
    if output.status == "not_found":
        if output.evidence:
            return Decision("needs_review", "model_uncertain", None)
        return Decision("not_found", None, output.explanation)
    quotes = _verified_quotes(output, shown)
    if quotes is None:
        return Decision("needs_review", "evidence_unverified", None)
    return Decision(output.status, None, output.explanation, quotes)

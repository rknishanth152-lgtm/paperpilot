"""What the model must return for one checklist item (R6; FR-REP-002).

Model output is untrusted input. `parse_assessment` accepts exactly this
structure. Whether the status is earned is decided by the rules afterwards, so a
contradiction is recorded as `needs_review` and not lost as a format error.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from app.schemas.answer import MalformedAnswerError


class _ModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceQuote(_ModelOutput):
    alias: str
    quote: str

    @field_validator("quote")
    @classmethod
    def quote_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("quote must not be blank")
        return value


class ModelAssessment(_ModelOutput):
    status: Literal["reported", "partially_reported", "not_found", "needs_review"]
    explanation: str | None
    evidence: tuple[EvidenceQuote, ...]

    @field_validator("explanation")
    @classmethod
    def explanation_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("explanation must not be blank")
        return value


def parse_assessment(text: str) -> ModelAssessment:
    """The validated output, or `MalformedAnswerError`."""
    try:
        return ModelAssessment.model_validate_json(text)
    except ValidationError:
        # Not chained: the error quotes the output, which is paper-derived text.
        raise MalformedAnswerError() from None


def assessment_json_schema() -> dict[str, Any]:
    return ModelAssessment.model_json_schema()

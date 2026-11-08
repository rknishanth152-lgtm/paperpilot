"""What the model must return for an answer (P5-T3; FR-QA-003, PRD §9.1).

Model output is untrusted input. `parse_answer` accepts exactly this structure
and rejects anything else: extra or missing fields, wrong types, free text.

This checks structure only. Whether a citation is real is decided later by the
citation validator (P5-T7): an unknown alias or an uncited statement is parsed
here so that it can be reported as `validation_status: failed` (FR-CIT-004).

Rules a JSON schema cannot carry for every provider, such as non-blank text,
are enforced in code, so `answer_json_schema` stays free of those keywords.
"""

from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)


class _ModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Citation(_ModelOutput):
    """A prompt-local alias (AD-007) and, if given, an exact quotation."""

    alias: str
    quote: str | None

    @field_validator("quote")
    @classmethod
    def quote_not_blank(cls, value: str | None) -> str | None:
        # A blank quote would be "found" in every passage.
        if value is not None and not value.strip():
            raise ValueError("quote must not be blank")
        return value


class Statement(_ModelOutput):
    text: str
    citations: tuple[Citation, ...]

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class ModelAnswer(_ModelOutput):
    statements: tuple[Statement, ...]
    evidence_sufficiency: Literal["sufficient", "partial", "insufficient"]
    limitations: str | None

    @model_validator(mode="after")
    def statements_match_sufficiency(self) -> Self:
        if self.evidence_sufficiency == "insufficient" and self.statements:
            raise ValueError("an insufficient answer has no statements")
        # Without this, an empty answer would pass as fully validated.
        if self.evidence_sufficiency != "insufficient" and not self.statements:
            raise ValueError("an answer claiming evidence needs a statement")
        return self


class MalformedAnswerError(Exception):
    """The model's output does not follow the contract. Never repeats the output."""

    code = "malformed_model_output"
    message = "The AI model returned a response in the wrong format."

    def __init__(self) -> None:
        super().__init__(self.code)


def parse_answer(text: str) -> ModelAnswer:
    """The validated answer, or `MalformedAnswerError`."""
    try:
        return ModelAnswer.model_validate_json(text)
    except ValidationError:
        # Not chained: the validation error quotes the output, which is paper
        # derived text and must not reach logs (NFR-PRI-002).
        raise MalformedAnswerError() from None


def answer_json_schema() -> dict[str, Any]:
    """The JSON Schema given to the model."""
    return ModelAnswer.model_json_schema()

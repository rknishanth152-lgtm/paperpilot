"""The retrieval evaluation set's format (P4-T5, FR-EVL-001).

Expected evidence is a paper plus a quote from its source text, never a
database id, because ids change on re-ingestion.
"""

from datetime import date
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_SET = REPO_ROOT / "benchmarks" / "retrieval_eval_v1.json"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CorpusPaper(_Strict):
    key: str
    title: str
    doi: str
    licence: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExpectedQuote(_Strict):
    paper: str
    quote: str = Field(min_length=20)


class Question(_Strict):
    id: str = Field(pattern=r"^q\d{2}$")
    question: str = Field(min_length=10)
    answerable: bool
    papers: list[str]
    expected_quotes: list[ExpectedQuote]

    @model_validator(mode="after")
    def evidence_matches_answerable(self) -> Self:
        if self.answerable and not self.expected_quotes:
            raise ValueError(f"{self.id}: an answerable question needs a quote")
        if not self.answerable and (self.expected_quotes or self.papers):
            raise ValueError(f"{self.id}: an unanswerable question has no evidence")
        if {quote.paper for quote in self.expected_quotes} - set(self.papers):
            raise ValueError(f"{self.id}: quote from a paper not listed")
        return self


class EvaluationSet(_Strict):
    name: str
    version: int
    status: Literal["draft", "reviewed"]
    created: date
    drafted_by: str
    reviewer: str | None
    review_date: date | None
    limits: str
    corpus: list[CorpusPaper]
    excluded_probe_queries: list[str]
    questions: list[Question]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.status == "reviewed") != (
            self.reviewer is not None and self.review_date is not None
        ):
            raise ValueError("reviewer and review_date are set exactly when reviewed")
        ids = [question.id for question in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("question ids must be unique")
        known = {paper.key for paper in self.corpus}
        for question in self.questions:
            if set(question.papers) - known:
                raise ValueError(f"{question.id}: unknown paper")
        return self


def load_evaluation_set(path: Path = EVALUATION_SET) -> EvaluationSet:
    return EvaluationSet.model_validate_json(path.read_text(encoding="utf-8"))

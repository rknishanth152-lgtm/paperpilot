"""Retrieval-only evaluation harness (P4-T6, FR-EVL-002).

Maps each expected quote to the stored passages that contain it, runs the
retriever without any LLM, and computes Recall@5: a question is a hit if any
expected passage is in the top 5. Each question is searched twice: across the
whole corpus (the main figure) and within its own paper.

A quote found in no passage is an unmatched expectation, a labelling problem,
so it is reported and never counted as a retrieval miss. Unanswerable questions
are listed but not scored: retrieval alone cannot tell that a question has no
answer.

Quotes are matched against stored passage text with the provisional OQ-013
rules (docs/experiments/grobid-feasibility.md).
"""

import json
import re
import unicodedata
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.evaluation.dataset import EvaluationSet, Question

from app.models import Document, Passage
from app.services.retrieval.keyword import search_passages

K = 5
_DASHES = re.compile("[‐-―−]")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
_SPLIT_LIGATURE = re.compile(r"(fi|fl|ff) (?=[a-z])")


class CorpusError(Exception):
    """A paper in the evaluation set is not available as a parsed document."""


class Retrieved(Protocol):
    @property
    def passage_id(self) -> uuid.UUID: ...

    @property
    def score(self) -> float: ...


Retriever = Callable[[str, int, Sequence[uuid.UUID]], Sequence[Retrieved]]


@dataclass(frozen=True)
class StoredPassage:
    passage_id: uuid.UUID
    document_id: uuid.UUID
    text: str


def normalize_for_matching(text: str) -> str:
    """Applied identically to quote and passage. Case is kept."""
    folded = _DASHES.sub("-", unicodedata.normalize("NFKC", text)).translate(_QUOTES)
    return _SPLIT_LIGATURE.sub(r"\1", " ".join(folded.split()))


def require_reviewed(evaluation: EvaluationSet) -> None:
    if evaluation.status != "reviewed":
        raise ValueError("the evaluation set has not been reviewed (FR-EVL-001)")


def load_corpus(
    sessions: sessionmaker[Session], evaluation: EvaluationSet
) -> tuple[dict[str, uuid.UUID], dict[str, list[StoredPassage]]]:
    """Each corpus paper's parsed document and passages, found by file hash."""
    documents: dict[str, uuid.UUID] = {}
    passages: dict[str, list[StoredPassage]] = {}
    with sessions() as session:
        for paper in evaluation.corpus:
            document_id = session.scalar(
                select(Document.id).where(
                    Document.sha256 == paper.sha256, Document.status == "parsed"
                )
            )
            if document_id is None:
                raise CorpusError(f"paper {paper.key} is not ingested and parsed")
            documents[paper.key] = document_id
            rows = session.execute(
                select(Passage.id, Passage.text)
                .where(Passage.document_id == document_id)
                .order_by(Passage.ordinal)
            )
            passages[paper.key] = [
                StoredPassage(row.id, document_id, row.text) for row in rows
            ]
    return documents, passages


def keyword_retriever(
    sessions: sessionmaker[Session], *, max_query_chars: int
) -> Retriever:
    def retrieve(
        question: str, k: int, document_ids: Sequence[uuid.UUID]
    ) -> Sequence[Retrieved]:
        return search_passages(
            sessions,
            question,
            k=k,
            max_query_chars=max_query_chars,
            document_ids=document_ids,
        )

    return retrieve


def _expected(
    question: Question, passages: Mapping[str, Sequence[StoredPassage]]
) -> tuple[list[uuid.UUID], list[str]]:
    expected: list[uuid.UUID] = []
    unmatched: list[str] = []
    for item in question.expected_quotes:
        wanted = normalize_for_matching(item.quote)
        found = [
            passage.passage_id
            for passage in passages.get(item.paper, ())
            if wanted in normalize_for_matching(passage.text)
        ]
        if found:
            expected.extend(found)
        else:
            unmatched.append(item.quote)
    return expected, unmatched


def _rank(ranked: Sequence[Retrieved], expected: Sequence[uuid.UUID]) -> int | None:
    for position, result in enumerate(ranked, 1):
        if result.passage_id in expected:
            return position
    return None


def _listing(ranked: Sequence[Retrieved]) -> list[dict[str, Any]]:
    return [
        {"passage_id": str(result.passage_id), "score": result.score}
        for result in ranked
    ]


def _recall(hits: int, evaluated: int) -> float | None:
    return hits / evaluated if evaluated else None


def evaluate(
    evaluation: EvaluationSet,
    documents: Mapping[str, uuid.UUID],
    passages: Mapping[str, Sequence[StoredPassage]],
    retrieve: Retriever,
    *,
    k: int = K,
) -> dict[str, Any]:
    """Per-question outcomes and the summary. Contains ids and scores, no paper text."""
    corpus = list(documents.values())
    rows: list[dict[str, Any]] = []
    evaluated = hits_all = hits_paper = unmatched_questions = unmatched_quotes = 0

    for question in evaluation.questions:
        ranked_all = list(retrieve(question.question, k, corpus))[:k]
        row: dict[str, Any] = {"id": question.id, "answerable": question.answerable}
        if not question.answerable:
            row.update(
                outcome="unanswerable",
                returned_all_papers=len(ranked_all),
                retrieved_all_papers=_listing(ranked_all),
            )
            rows.append(row)
            continue

        expected, unmatched = _expected(question, passages)
        unmatched_quotes += len(unmatched)
        row.update(
            expected_passage_ids=[str(passage_id) for passage_id in expected],
            unmatched_quotes=unmatched,
            retrieved_all_papers=_listing(ranked_all),
        )
        if not expected:
            unmatched_questions += 1
            row.update(
                outcome="unmatched", rank_all_papers=None, rank_question_paper=None
            )
            rows.append(row)
            continue

        scope = [documents[paper] for paper in question.papers]
        ranked_paper = list(retrieve(question.question, k, scope))[:k]
        rank_all = _rank(ranked_all, expected)
        rank_paper = _rank(ranked_paper, expected)
        evaluated += 1
        hits_all += rank_all is not None
        hits_paper += rank_paper is not None
        row.update(
            outcome="hit" if rank_all is not None else "miss",
            rank_all_papers=rank_all,
            rank_question_paper=rank_paper,
            retrieved_question_paper=_listing(ranked_paper),
        )
        rows.append(row)

    return {
        "summary": {
            "k": k,
            "questions": len(evaluation.questions),
            "answerable": sum(q.answerable for q in evaluation.questions),
            "evaluated": evaluated,
            "unmatched_questions": unmatched_questions,
            "unmatched_quotes": unmatched_quotes,
            "hits_all_papers": hits_all,
            "recall_at_k_all_papers": _recall(hits_all, evaluated),
            "hits_question_paper": hits_paper,
            "recall_at_k_question_paper": _recall(hits_paper, evaluated),
        },
        "questions": rows,
    }


def result_record(
    result: Mapping[str, Any],
    *,
    evaluation: EvaluationSet,
    evaluation_sha256: str,
    run_at: datetime,
    code_revision: str,
    working_tree_clean: bool,
    configuration: Mapping[str, Any],
) -> dict[str, Any]:
    """The result with what is needed to reproduce and interpret it."""
    return {
        "run_at": run_at.isoformat(),
        "code_revision": code_revision,
        "working_tree_clean": working_tree_clean,
        "configuration": dict(configuration),
        "evaluation_set": {
            "version": evaluation.version,
            "sha256": evaluation_sha256,
            "status": evaluation.status,
            "reviewer": evaluation.reviewer,
            "review_date": str(evaluation.review_date),
            "questions": len(evaluation.questions),
        },
        "limits": evaluation.limits,
        **result,
    }


def write_result(record: Mapping[str, Any], directory: Path) -> Path:
    """Save to a new dated file. An existing result is never overwritten."""
    stamp = datetime.fromisoformat(record["run_at"]).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"retrieval-{stamp}-{record['code_revision'][:7]}.json"
    directory.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path

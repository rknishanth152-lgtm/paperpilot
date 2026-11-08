"""The harness end to end with real retrieval on synthetic passages (P4-T6, FR-RET-004)."""

import hashlib
import uuid

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.evaluation.dataset import EvaluationSet
from tests.evaluation.retrieval_harness import (
    CorpusError,
    evaluate,
    keyword_retriever,
    load_corpus,
)
from tests.integration.test_keyword_retrieval import add_document

from app.models import Document

OTHER_SHA = hashlib.sha256(b"other").hexdigest()


def sha_of(sessions: sessionmaker[Session], document_id: uuid.UUID) -> str:
    with sessions() as session:
        document = session.get(Document, document_id)
        assert document is not None
        return document.sha256


def evaluation_with(shas: dict[str, str]) -> EvaluationSet:
    return EvaluationSet.model_validate(
        {
            "name": "n",
            "version": 1,
            "status": "reviewed",
            "created": "2026-11-08",
            "drafted_by": "d",
            "reviewer": "someone",
            "review_date": "2026-11-08",
            "limits": "small",
            "corpus": [
                {"key": k, "title": "t", "doi": "d", "licence": "l", "sha256": v}
                for k, v in shas.items()
            ],
            "excluded_probe_queries": [],
            "questions": [
                {
                    "id": "q01",
                    "question": "Why did the mountain glaciers retreat?",
                    "answerable": True,
                    "papers": ["p1"],
                    "expected_quotes": [
                        {
                            "paper": "p1",
                            "quote": "glaciers retreated because of warming",
                        }
                    ],
                },
                {
                    "id": "q02",
                    "question": "When did the volcano erupt most recently?",
                    "answerable": True,
                    "papers": ["p2"],
                    "expected_quotes": [
                        {"paper": "p2", "quote": "a sentence that was never stored"}
                    ],
                },
            ],
        }
    )


def test_full_run_on_stored_passages(sessions: sessionmaker[Session]) -> None:
    first = add_document(
        sessions, "The glaciers retreated because of warming.", "Rocks."
    )
    second = add_document(sessions, "Volcanoes erupted.")
    evaluation = evaluation_with(
        {"p1": sha_of(sessions, first), "p2": sha_of(sessions, second)}
    )

    documents, passages = load_corpus(sessions, evaluation)
    result = evaluate(
        evaluation,
        documents,
        passages,
        keyword_retriever(sessions, max_query_chars=2000),
    )

    assert documents == {"p1": first, "p2": second}
    assert [row["outcome"] for row in result["questions"]] == ["hit", "unmatched"]
    assert result["questions"][0]["rank_all_papers"] == 1
    assert result["summary"]["recall_at_k_all_papers"] == 1.0


def test_a_corpus_paper_that_was_not_ingested_stops_the_run(
    sessions: sessionmaker[Session],
) -> None:
    evaluation = evaluation_with(
        {"p1": hashlib.sha256(b"absent").hexdigest(), "p2": OTHER_SHA}
    )

    with pytest.raises(CorpusError, match="p1"):
        load_corpus(sessions, evaluation)


def test_a_corpus_paper_that_is_not_parsed_stops_the_run(
    sessions: sessionmaker[Session],
) -> None:
    failed = add_document(sessions, status="failed")
    evaluation = evaluation_with({"p1": sha_of(sessions, failed), "p2": OTHER_SHA})

    with pytest.raises(CorpusError, match="p1"):
        load_corpus(sessions, evaluation)

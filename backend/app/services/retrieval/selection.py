"""The retrieval method answering uses (R4; FR-RET-007).

Semantic search is the default on recorded results
(docs/experiments/retrieval-comparison.md).

A selected passage without an embedding is not a failure: new uploads are not
embedded automatically. The whole selection then uses keyword search and the
result names that method, so a paper is never reported as having no match only
because it has no embeddings. A provider failure stays an explicit error.
"""

import logging
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.services.embeddings import Embedder
from app.services.llm_factory import build_embedder
from app.services.retrieval.keyword import RetrievedPassage, search_passages
from app.services.retrieval.semantic import search_semantic

logger = logging.getLogger(__name__)

KEYWORD_METHOD = "keyword_full_text"
SEMANTIC_METHOD = "semantic_cosine"


@dataclass(frozen=True)
class Retrieval:
    passages: list[RetrievedPassage]
    method: str


class Retriever(Protocol):
    @property
    def name(self) -> str: ...

    def __call__(
        self,
        question: str,
        *,
        k: int,
        max_query_chars: int,
        document_ids: Collection[uuid.UUID] | None,
        paper_ids: Collection[uuid.UUID] | None,
    ) -> Retrieval: ...


class KeywordRetriever:
    name = KEYWORD_METHOD

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def __call__(
        self,
        question: str,
        *,
        k: int,
        max_query_chars: int,
        document_ids: Collection[uuid.UUID] | None,
        paper_ids: Collection[uuid.UUID] | None,
    ) -> Retrieval:
        passages = search_passages(
            self._sessions,
            question,
            k=k,
            max_query_chars=max_query_chars,
            document_ids=document_ids,
            paper_ids=paper_ids,
        )
        return Retrieval(passages, KEYWORD_METHOD)


class SemanticRetriever:
    name = SEMANTIC_METHOD

    def __init__(self, sessions: sessionmaker[Session], embedder: Embedder) -> None:
        self._sessions = sessions
        self._embedder = embedder
        self._keyword = KeywordRetriever(sessions)

    def __call__(
        self,
        question: str,
        *,
        k: int,
        max_query_chars: int,
        document_ids: Collection[uuid.UUID] | None,
        paper_ids: Collection[uuid.UUID] | None,
    ) -> Retrieval:
        result = search_semantic(
            self._sessions,
            self._embedder,
            question,
            k=k,
            max_query_chars=max_query_chars,
            document_ids=document_ids,
            paper_ids=paper_ids,
        )
        if result.missing_embeddings:
            logger.info("retrieval keyword_used missing=%d", result.missing_embeddings)
            return self._keyword(
                question,
                k=k,
                max_query_chars=max_query_chars,
                document_ids=document_ids,
                paper_ids=paper_ids,
            )
        return Retrieval(result.passages, SEMANTIC_METHOD)


def build_retriever(settings: Settings, sessions: sessionmaker[Session]) -> Retriever:
    """Semantic when chosen and the API key belongs to the embedding provider."""
    if (
        settings.retrieval_method == "semantic"
        and settings.llm_provider == settings.embedding_provider
    ):
        return SemanticRetriever(sessions, build_embedder(settings))
    return KeywordRetriever(sessions)

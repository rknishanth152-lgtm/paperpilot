"""Embed stored passages that do not have an embedding yet (R2; FR-RET-005).

Each batch is saved before the next is sent, so a run stopped by a rate limit
keeps its progress and the next run carries on. Only `parsed` documents count.

Logs carry counts only, never passage text (NFR-PRI-002).
"""

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Document, Paper, Passage, PassageEmbedding
from app.services.embeddings import (
    DocumentText,
    Embedder,
    EmbeddingDimensionError,
)
from app.services.llm import ModelError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingRun:
    embedded: int
    missing: int
    stopped_by: str | None  # the failure's code when the run stopped early


@dataclass(frozen=True)
class _Pending:
    passage_id: uuid.UUID
    document: DocumentText


def _is_missing[*Ts](model: str, statement: Select[*Ts]) -> Select[*Ts]:
    has_embedding = exists().where(
        PassageEmbedding.passage_id == Passage.id,
        PassageEmbedding.model == model,
    )
    return statement.join(Document, Passage.document_id == Document.id).where(
        Document.status == "parsed", ~has_embedding
    )


def count_missing_embeddings(sessions: sessionmaker[Session], model: str) -> int:
    """How many passages in `parsed` documents have no embedding from `model`."""
    with sessions() as session:
        return int(
            session.scalar(_is_missing(model, select(func.count(Passage.id)))) or 0
        )


def _pending(sessions: sessionmaker[Session], model: str) -> list[_Pending]:
    statement = (
        _is_missing(model, select(Passage.id, Passage.text, Paper.title))
        .join(Paper, Document.paper_id == Paper.id)
        .order_by(Passage.id)
    )
    with sessions() as session:
        rows = session.execute(statement).all()
    return [_Pending(row.id, DocumentText(row.title, row.text)) for row in rows]


def _refuse_a_different_size(
    sessions: sessionmaker[Session], embedder: Embedder
) -> None:
    with sessions() as session:
        different = session.scalar(
            select(
                exists().where(
                    PassageEmbedding.model == embedder.model_name,
                    PassageEmbedding.dimensions != embedder.dimensions,
                )
            )
        )
    if different:
        raise EmbeddingDimensionError()


def _store(
    sessions: sessionmaker[Session],
    embedder: Embedder,
    batch: list[_Pending],
    vectors: list[list[float]],
) -> None:
    with sessions.begin() as session:
        session.add_all(
            PassageEmbedding(
                passage_id=item.passage_id,
                model=embedder.model_name,
                text_format=embedder.text_format,
                dimensions=embedder.dimensions,
                embedding=vector,
            )
            for item, vector in zip(batch, vectors, strict=True)
        )


def embed_missing(
    sessions: sessionmaker[Session],
    embedder: Embedder,
    *,
    batch_size: int,
    pause_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
) -> EmbeddingRun:
    """Embed what is missing. A model failure stops the run and is reported.

    Raises EmbeddingDimensionError, before sending anything, if this model's
    stored embeddings have a different size from the embedder's.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    _refuse_a_different_size(sessions, embedder)
    pending = _pending(sessions, embedder.model_name)
    embedded = 0
    for start in range(0, len(pending), batch_size):
        if start:
            sleep(pause_seconds)
        batch = pending[start : start + batch_size]
        try:
            vectors = embedder.embed_documents([item.document for item in batch])
        except ModelError as error:
            logger.warning(
                "embedding stopped code=%s embedded=%d missing=%d",
                error.code,
                embedded,
                len(pending) - embedded,
            )
            return EmbeddingRun(embedded, len(pending) - embedded, error.code)
        _store(sessions, embedder, batch, vectors)
        embedded += len(batch)
    logger.info("embedding finished embedded=%d", embedded)
    return EmbeddingRun(embedded, 0, None)

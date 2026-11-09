"""Hybrid retrieval: keyword and semantic merged by rank (R3; FR-RET-006).

Reciprocal Rank Fusion adds 1 / (constant + rank) across the lists, using only
positions, because keyword and semantic scores are not on the same scale.

If semantic search cannot run, keyword results still answer and the result says
so. Keyword search uses the same database as semantic search, so a database
failure stops both and is raised.

Logs carry counts and codes only (NFR-PRI-002).
"""

import logging
import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace

from sqlalchemy.orm import Session, sessionmaker

from app.services.embeddings import Embedder
from app.services.llm import ModelError
from app.services.retrieval.keyword import RetrievedPassage, search_passages
from app.services.retrieval.semantic import search_semantic

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HybridResult:
    passages: list[RetrievedPassage]
    methods: tuple[str, ...]  # those with a passage in `passages`
    missing_embeddings: int
    semantic_failure: str | None  # the failure's code, if semantic could not run


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[RetrievedPassage]],
    *,
    k: int,
    constant: int,
) -> list[RetrievedPassage]:
    """The `k` best by fused rank; ties go to the lower passage id.

    Each returned passage's `score` is its fused score.
    """
    if k < 1 or constant < 1:
        raise ValueError("k and constant must be positive")
    scores: dict[uuid.UUID, float] = {}
    passages: dict[uuid.UUID, RetrievedPassage] = {}
    for ranked in ranked_lists:
        for rank, passage in enumerate(ranked, start=1):
            scores[passage.passage_id] = scores.get(passage.passage_id, 0.0) + (
                1 / (constant + rank)
            )
            passages.setdefault(passage.passage_id, passage)
    best = sorted(scores, key=lambda passage_id: (-scores[passage_id], passage_id))[:k]
    return [
        replace(passages[passage_id], score=scores[passage_id]) for passage_id in best
    ]


def search_hybrid(
    sessions: sessionmaker[Session],
    embedder: Embedder,
    question: str,
    *,
    k: int,
    candidates: int,
    rrf_constant: int,
    max_query_chars: int,
    document_ids: Collection[uuid.UUID] | None = None,
    paper_ids: Collection[uuid.UUID] | None = None,
) -> HybridResult:
    """Fuse each method's `candidates` best passages into the `k` best."""
    if candidates < k:
        raise ValueError("candidates must be at least k")
    keyword = search_passages(
        sessions,
        question,
        k=candidates,
        max_query_chars=max_query_chars,
        document_ids=document_ids,
        paper_ids=paper_ids,
    )
    semantic: list[RetrievedPassage] = []
    missing = 0
    failure: str | None = None
    try:
        found = search_semantic(
            sessions,
            embedder,
            question,
            k=candidates,
            max_query_chars=max_query_chars,
            document_ids=document_ids,
            paper_ids=paper_ids,
        )
    except ModelError as error:
        failure = error.code
        logger.warning("hybrid semantic_unavailable code=%s", error.code)
    else:
        semantic, missing = found.passages, found.missing_embeddings

    fused = reciprocal_rank_fusion([keyword, semantic], k=k, constant=rrf_constant)
    final = {passage.passage_id for passage in fused}
    methods = tuple(
        name
        for name, ranked in (("keyword", keyword), ("semantic", semantic))
        if any(passage.passage_id in final for passage in ranked)
    )
    logger.info(
        "hybrid k=%d keyword=%d semantic=%d results=%d",
        k,
        len(keyword),
        len(semantic),
        len(fused),
    )
    return HybridResult(fused, methods, missing, failure)

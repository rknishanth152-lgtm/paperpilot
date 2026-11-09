"""Embed stored passages with the configured embedding model (R2; FR-RET-005).

    uv run python scripts/embed_passages.py --check
    uv run python scripts/embed_passages.py

Without `--check` this sends passage text to the embedding provider. It is safe
to run again: finished passages are skipped. Exits with 1 if the run stops early.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings
from app.database import get_sessionmaker
from app.services.llm import ModelError
from app.services.llm_factory import build_embedder
from app.services.retrieval.embedding_job import (
    count_missing_embeddings,
    embed_missing,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report how many passages are missing an embedding, and send nothing",
    )
    options = parser.parse_args()
    settings = get_settings()
    sessions = get_sessionmaker()
    if options.check:
        missing = count_missing_embeddings(sessions, settings.embedding_model)
        print(f"Missing embeddings for {settings.embedding_model}: {missing}")
        return 0
    try:
        run = embed_missing(
            sessions,
            build_embedder(settings),
            batch_size=settings.embedding_batch_size,
            pause_seconds=settings.embedding_pause_seconds,
        )
    except ModelError as error:
        print(f"Stopped: {error.code}")
        return 1
    print(f"Embedded: {run.embedded}. Still missing: {run.missing}.")
    if run.stopped_by:
        print(f"Stopped early: {run.stopped_by}. Run the command again to continue.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

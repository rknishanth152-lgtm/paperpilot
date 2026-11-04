"""Startup recovery of interrupted documents (P3-T7, FR-ING-010, AD-010).

Ingestion runs inside the single API process (AD-010), so when the server
starts nothing can genuinely be processing: every `processing` document was
interrupted by a crash, a restart, or a database failure in the final
ingestion step. Each becomes `failed` / `interrupted` and may be retried.

This relies on running one server process. With several worker processes,
one worker's startup would mark another's live work as interrupted.
FR-ING-010's alternative ("or after a timeout") is not implemented: it would
need a periodic job, which this design does not have.
"""

import logging
import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.models import Document

logger = logging.getLogger(__name__)

INTERRUPTED_MESSAGE = (
    "Processing was interrupted before it finished (the server stopped). "
    "Retry the document."
)


def recover_interrupted(sessions: sessionmaker[Session]) -> list[uuid.UUID]:
    """Mark every `processing` document `failed` / `interrupted`; return their ids."""
    with sessions.begin() as session:
        recovered = list(
            session.scalars(
                update(Document)
                .where(Document.status == "processing")
                .values(
                    status="failed",
                    failure_reason="interrupted",
                    failure_message=INTERRUPTED_MESSAGE,
                )
                .returning(Document.id)
            )
        )
    for document_id in recovered:
        logger.warning(
            "ingestion document_id=%s status=failed reason=interrupted", document_id
        )
    logger.info("startup recovery recovered=%d", len(recovered))
    return recovered

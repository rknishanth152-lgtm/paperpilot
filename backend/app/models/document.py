import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.constraints import DOCUMENT_STATUSES, FAILURE_REASONS, one_of


class Document(Base):
    """One uploaded file, identified by its content hash. docs/design/schema.md §4."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("sha256"),
        UniqueConstraint("storage_key"),
        UniqueConstraint("tei_storage_key"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("storage_key <> ''", name="storage_key_not_empty"),
        CheckConstraint("tei_storage_key <> ''", name="tei_storage_key_not_empty"),
        CheckConstraint(
            "char_length(original_filename) BETWEEN 1 AND 255",
            name="original_filename_length",
        ),
        CheckConstraint(one_of("status", DOCUMENT_STATUSES), name="status_valid"),
        CheckConstraint(
            one_of("failure_reason", FAILURE_REASONS), name="failure_reason_valid"
        ),
        CheckConstraint(
            "char_length(failure_message) <= 1000", name="failure_message_length"
        ),
        CheckConstraint(
            "(status = 'failed') = (failure_reason IS NOT NULL)",
            name="failure_reason_iff_failed",
        ),
        CheckConstraint(
            "failure_message IS NULL OR status = 'failed'",
            name="failure_message_only_when_failed",
        ),
        CheckConstraint(
            "status <> 'parsed' OR (paper_id IS NOT NULL AND parser_name IS NOT NULL "
            "AND parser_version IS NOT NULL AND tei_storage_key IS NOT NULL)",
            name="parsed_is_complete",
        ),
        CheckConstraint(
            "status <> 'processing' OR processing_started_at IS NOT NULL",
            name="processing_has_start",
        ),
        CheckConstraint("page_count > 0", name="page_count_positive"),
        CheckConstraint("skipped_paragraphs >= 0", name="skipped_not_negative"),
        CheckConstraint("joined_paragraphs >= 0", name="joined_not_negative"),
        # Startup recovery scan for documents left processing (FR-ING-010).
        Index(
            "ix_documents_processing",
            "processing_started_at",
            postgresql_where=text("status = 'processing'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("uuidv7()")
    )
    paper_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("papers.id", ondelete="RESTRICT"), index=True
    )
    sha256: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    failure_message: Mapped[str | None] = mapped_column(Text)
    parser_name: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str | None] = mapped_column(Text)
    parser_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tei_storage_key: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    skipped_paragraphs: Mapped[int | None] = mapped_column(Integer)
    joined_paragraphs: Mapped[int | None] = mapped_column(Integer)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

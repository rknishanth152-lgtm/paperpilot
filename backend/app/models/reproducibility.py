import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.constraints import (
    DOCUMENT_STATUSES,
    REPRODUCIBILITY_REVIEW_REASONS,
    REPRODUCIBILITY_STATUSES,
    one_of,
)


class ReproducibilityAssessment(Base):
    """One run of the checklist over one document (FR-REP-001, FR-REP-002).

    A re-run adds a new row, so earlier assessments stay (DR-008). `model` is
    null when no model was called, as for a document that was not parsed.
    """

    __tablename__ = "reproducibility_assessments"
    __table_args__ = (
        CheckConstraint("checklist_version <> ''", name="checklist_version_not_empty"),
        CheckConstraint(
            one_of("document_status", DOCUMENT_STATUSES), name="document_status_valid"
        ),
        CheckConstraint("model <> ''", name="model_not_empty"),
        CheckConstraint("prompt_version <> ''", name="prompt_version_not_empty"),
        CheckConstraint(
            "(model IS NULL) = (prompt_version IS NULL)", name="model_with_prompt"
        ),
        CheckConstraint("retrieval_method <> ''", name="retrieval_method_not_empty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=sql_text("uuidv7()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT")
    )
    checklist_version: Mapped[str] = mapped_column(Text)
    # The material examined: the document's status when it was assessed.
    document_status: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    retrieval_method: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ReproducibilityItem(Base):
    """One checklist item's status. Interpretation, apart from passages (DR-002)."""

    __tablename__ = "reproducibility_items"
    __table_args__ = (
        UniqueConstraint("assessment_id", "item_key"),
        CheckConstraint("item_key <> ''", name="item_key_not_empty"),
        CheckConstraint(
            one_of("status", REPRODUCIBILITY_STATUSES), name="status_valid"
        ),
        CheckConstraint(
            one_of("review_reason", REPRODUCIBILITY_REVIEW_REASONS),
            name="review_reason_valid",
        ),
        CheckConstraint(
            "(status = 'needs_review') = (review_reason IS NOT NULL)",
            name="review_reason_only_for_review",
        ),
        CheckConstraint("explanation <> ''", name="explanation_not_empty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=sql_text("uuidv7()")
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reproducibility_assessments.id", ondelete="RESTRICT")
    )
    item_key: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    review_reason: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)


class ReproducibilityItemPassage(Base):
    """A passage examined for an item. A `quote` makes it verified evidence.

    Null `quote` means the passage was examined and quoted nothing (FR-REP-002).
    """

    __tablename__ = "reproducibility_item_passages"
    __table_args__ = (
        UniqueConstraint("item_id", "passage_id"),
        CheckConstraint("quote <> ''", name="quote_not_empty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=sql_text("uuidv7()")
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reproducibility_items.id", ondelete="RESTRICT")
    )
    passage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("passages.id", ondelete="RESTRICT")
    )
    quote: Mapped[str | None] = mapped_column(Text)

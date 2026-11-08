import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.constraints import PASSAGE_REGIONS, one_of

SECTION_PATH_SQL = (
    "CASE WHEN section_number IS NULL THEN section_title "
    "ELSE section_number || ' ' || section_title END"
)

# The configuration is named so the column never depends on the session's
# default_text_search_config (docs/design/retrieval.md).
SEARCH_VECTOR_SQL = "to_tsvector('english'::regconfig, text)"


class Passage(Base):
    """Immutable source text (DR-002, DR-004). docs/design/schema.md §5.

    Rows are never updated: a database trigger rejects UPDATE (created in the
    migration, not here).
    """

    __tablename__ = "passages"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal"),
        CheckConstraint("ordinal >= 0", name="ordinal_not_negative"),
        CheckConstraint(one_of("region", PASSAGE_REGIONS), name="region_valid"),
        CheckConstraint(
            "back_type IS NULL OR region = 'back'", name="back_type_only_for_back"
        ),
        CheckConstraint("back_type <> ''", name="back_type_not_empty"),
        CheckConstraint("section_number <> ''", name="section_number_not_empty"),
        CheckConstraint("section_title <> ''", name="section_title_not_empty"),
        CheckConstraint("text <> ''", name="text_not_empty"),
        CheckConstraint("page_start >= 1", name="page_start_positive"),
        CheckConstraint(
            "(page_start IS NULL) = (page_end IS NULL)", name="pages_both_or_neither"
        ),
        CheckConstraint("page_end >= page_start", name="page_order"),
        Index("ix_passages_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=sql_text("uuidv7()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT")
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    region: Mapped[str] = mapped_column(Text)
    back_type: Mapped[str | None] = mapped_column(Text)
    section_number: Mapped[str | None] = mapped_column(Text)
    section_title: Mapped[str | None] = mapped_column(Text)
    section_path: Mapped[str | None] = mapped_column(
        Text, Computed(SECTION_PATH_SQL, persisted=True)
    )
    text: Mapped[str] = mapped_column(Text)
    # Derived from `text` by the database (FR-RET-001). Deferred so that
    # loading passages never fetches it; only retrieval needs it.
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, Computed(SEARCH_VECTOR_SQL, persisted=True), deferred=True
    )
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

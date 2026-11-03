import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.constraints import METADATA_SOURCES, one_of


class Paper(Base):
    """A scholarly work at metadata level (PRD §1.6). docs/design/schema.md §3."""

    __tablename__ = "papers"
    __table_args__ = (
        UniqueConstraint("doi_normalized"),
        CheckConstraint("title <> ''", name="title_not_empty"),
        CheckConstraint("abstract <> ''", name="abstract_not_empty"),
        CheckConstraint("doi <> ''", name="doi_not_empty"),
        CheckConstraint("doi_normalized LIKE '10.%'", name="doi_normalized_format"),
        CheckConstraint("(doi IS NULL) = (doi_normalized IS NULL)", name="doi_pair"),
        CheckConstraint(
            one_of("metadata_source", METADATA_SOURCES), name="metadata_source_valid"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("uuidv7()")
    )
    title: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    abstract: Mapped[str | None] = mapped_column(Text)
    doi: Mapped[str | None] = mapped_column(Text)
    doi_normalized: Mapped[str | None] = mapped_column(Text)
    metadata_source: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

import json
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import text as sql_text
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.models.base import Base


class Vector(UserDefinedType[list[float]]):
    """pgvector's `vector`, exchanged in its text form `[1.0,2.0]`.

    No size is fixed on the column, so a different model needs no migration;
    `dimensions` records the size of each row and a constraint checks it.
    """

    cache_ok = True

    def get_col_spec(self, **_: Any) -> str:
        return "vector"

    def bind_processor(
        self, dialect: Dialect
    ) -> Callable[[list[float] | None], str | None]:
        def process(value: list[float] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(repr(float(item)) for item in value) + "]"

        return process

    def result_processor(
        self, dialect: Dialect, coltype: object
    ) -> Callable[[str | None], list[float] | None]:
        def process(value: str | None) -> list[float] | None:
            return None if value is None else [float(x) for x in json.loads(value)]

        return process


class PassageEmbedding(Base):
    """A machine-made vector for a passage, by model (AD-014, DR-005).

    Kept apart from `passages`, which stay immutable source text (DR-002).
    """

    __tablename__ = "passage_embeddings"
    __table_args__ = (
        UniqueConstraint("passage_id", "model"),
        CheckConstraint("model <> ''", name="model_not_empty"),
        CheckConstraint("text_format <> ''", name="text_format_not_empty"),
        CheckConstraint("dimensions > 0", name="dimensions_positive"),
        CheckConstraint(
            "vector_dims(embedding) = dimensions", name="dimensions_match_embedding"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=sql_text("uuidv7()")
    )
    passage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("passages.id", ondelete="RESTRICT")
    )
    model: Mapped[str] = mapped_column(Text)
    text_format: Mapped[str] = mapped_column(Text)
    dimensions: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(Vector)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

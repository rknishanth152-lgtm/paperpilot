"""add passage embeddings

Enables pgvector and adds a table of embeddings keyed by passage and model
(R2, FR-RET-005, AD-014). Passages are not changed. There is no approximate
index: search is exact, for the reasons in docs/design/embeddings.md.

Revision ID: f4a9c1d27b60
Revises: e3ab5ad233d7
Create Date: 2026-11-09 16:30:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a9c1d27b60"
down_revision: str | Sequence[str] | None = "e3ab5ad233d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class _Vector(sa.types.UserDefinedType[list[float]]):
    cache_ok = True

    def get_col_spec(self, **_: Any) -> str:
        return "vector"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION vector")
    op.create_table(
        "passage_embeddings",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("passage_id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("text_format", sa.Text(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", _Vector(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "model <> ''", name=op.f("ck_passage_embeddings_model_not_empty")
        ),
        sa.CheckConstraint(
            "text_format <> ''",
            name=op.f("ck_passage_embeddings_text_format_not_empty"),
        ),
        sa.CheckConstraint(
            "dimensions > 0", name=op.f("ck_passage_embeddings_dimensions_positive")
        ),
        sa.CheckConstraint(
            "vector_dims(embedding) = dimensions",
            name=op.f("ck_passage_embeddings_dimensions_match_embedding"),
        ),
        sa.ForeignKeyConstraint(
            ["passage_id"],
            ["passages.id"],
            name=op.f("fk_passage_embeddings_passage_id_passages"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passage_embeddings")),
        sa.UniqueConstraint(
            "passage_id",
            "model",
            name=op.f("uq_passage_embeddings_passage_id_model"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("passage_embeddings")
    op.execute("DROP EXTENSION vector")

"""add passage search vector

Full-text search representation for passages (P4-T2, FR-RET-001). A stored
generated column, so every passage, existing or new, is searchable with no
manual step. Adding it rewrites the table without firing row triggers, so the
immutability trigger (DR-004) is unaffected and passage text does not change.
Configuration: docs/design/retrieval.md.

Revision ID: e3ab5ad233d7
Revises: d2ea199dd3d3
Create Date: 2026-11-08 22:35:16.919618

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e3ab5ad233d7"
down_revision: str | Sequence[str] | None = "d2ea199dd3d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "passages",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english'::regconfig, text)", persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_passages_search_vector",
        "passages",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_passages_search_vector", table_name="passages", postgresql_using="gin"
    )
    op.drop_column("passages", "search_vector")

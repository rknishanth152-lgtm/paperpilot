"""add reproducibility assessments

Tables for checklist assessments, their item statuses and the passages examined
for each item (R5, FR-REP-001, FR-REP-002, AD-013). Interpretation only: passages
are not changed. A re-run adds rows, so earlier assessments stay (DR-008).

Revision ID: a7d3e5f1c829
Revises: f4a9c1d27b60
Create Date: 2026-11-09 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7d3e5f1c829"
down_revision: str | Sequence[str] | None = "f4a9c1d27b60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "reproducibility_assessments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("checklist_version", sa.Text(), nullable=False),
        sa.Column("document_status", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("retrieval_method", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "checklist_version <> ''",
            name=op.f("ck_reproducibility_assessments_checklist_version_not_empty"),
        ),
        sa.CheckConstraint(
            "document_status IN ('pending', 'processing', 'parsed', 'failed')",
            name=op.f("ck_reproducibility_assessments_document_status_valid"),
        ),
        sa.CheckConstraint(
            "model <> ''", name=op.f("ck_reproducibility_assessments_model_not_empty")
        ),
        sa.CheckConstraint(
            "prompt_version <> ''",
            name=op.f("ck_reproducibility_assessments_prompt_version_not_empty"),
        ),
        sa.CheckConstraint(
            "(model IS NULL) = (prompt_version IS NULL)",
            name=op.f("ck_reproducibility_assessments_model_with_prompt"),
        ),
        sa.CheckConstraint(
            "retrieval_method <> ''",
            name=op.f("ck_reproducibility_assessments_retrieval_method_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_reproducibility_assessments_document_id_documents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reproducibility_assessments")),
    )
    op.create_table(
        "reproducibility_items",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("item_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "item_key <> ''", name=op.f("ck_reproducibility_items_item_key_not_empty")
        ),
        sa.CheckConstraint(
            "status IN ('reported', 'partially_reported', 'not_found', 'needs_review')",
            name=op.f("ck_reproducibility_items_status_valid"),
        ),
        sa.CheckConstraint(
            "review_reason IN "
            "('parse_incomplete', 'evidence_unverified', 'model_uncertain')",
            name=op.f("ck_reproducibility_items_review_reason_valid"),
        ),
        sa.CheckConstraint(
            "(status = 'needs_review') = (review_reason IS NOT NULL)",
            name=op.f("ck_reproducibility_items_review_reason_only_for_review"),
        ),
        sa.CheckConstraint(
            "explanation <> ''",
            name=op.f("ck_reproducibility_items_explanation_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["reproducibility_assessments.id"],
            name=op.f(
                "fk_reproducibility_items_assessment_id_reproducibility_assessments"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reproducibility_items")),
        sa.UniqueConstraint(
            "assessment_id",
            "item_key",
            name=op.f("uq_reproducibility_items_assessment_id_item_key"),
        ),
    )
    op.create_table(
        "reproducibility_item_passages",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("passage_id", sa.Uuid(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "quote <> ''",
            name=op.f("ck_reproducibility_item_passages_quote_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["reproducibility_items.id"],
            name=op.f("fk_reproducibility_item_passages_item_id_reproducibility_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["passage_id"],
            ["passages.id"],
            name=op.f("fk_reproducibility_item_passages_passage_id_passages"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reproducibility_item_passages")),
        sa.UniqueConstraint(
            "item_id",
            "passage_id",
            name=op.f("uq_reproducibility_item_passages_item_id_passage_id"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("reproducibility_item_passages")
    op.drop_table("reproducibility_items")
    op.drop_table("reproducibility_assessments")

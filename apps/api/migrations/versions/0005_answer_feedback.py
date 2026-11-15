"""Add explicitly submitted user feedback; preserve all existing evidence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "answer_feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspace.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("rating", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(32)),
        sa.Column("comment", sa.Text()),
        sa.Column("answer", JSONB(), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "created_by", "submission_id", name="uq_feedback_submission"
        ),
        sa.CheckConstraint("rating IN ('helpful', 'not_helpful')", name="ck_feedback_rating"),
        sa.CheckConstraint("mode IN ('keyword', 'semantic', 'hybrid')", name="ck_feedback_mode"),
        sa.CheckConstraint(
            "reason IS NULL OR (rating = 'not_helpful' AND reason IN "
            "('missing_evidence', 'irrelevant_evidence', 'other'))",
            name="ck_feedback_reason",
        ),
    )
    op.create_index(
        "ix_feedback_workspace_created", "answer_feedback", ["workspace_id", "created_at", "id"]
    )


def downgrade() -> None:
    op.drop_table("answer_feedback")

"""Add cited decision proposals, terminal reviews and approved decisions."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_proposal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspace.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            sa.Uuid(),
            sa.ForeignKey("source_chunk.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("extractor_version", sa.String(100), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.UniqueConstraint("chunk_id", "extractor_version", name="uq_proposal_chunk_extractor"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_proposal_status"
        ),
    )
    op.create_index(
        "ix_proposal_workspace_created", "knowledge_proposal", ["workspace_id", "created_at", "id"]
    )
    op.create_table(
        "review_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "proposal_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_proposal.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("reviewer_id", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("action IN ('approve', 'reject')", name="ck_review_action"),
    )
    op.create_table(
        "approved_decision",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspace.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "proposal_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_proposal.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_decision_workspace_created", "approved_decision", ["workspace_id", "created_at", "id"]
    )


def downgrade() -> None:
    op.drop_table("approved_decision")
    op.drop_table("review_event")
    op.drop_table("knowledge_proposal")

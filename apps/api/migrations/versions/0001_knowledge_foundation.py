"""Workspace-scoped immutable sources, versions, and evidence chunks."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TSVECTOR

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "source_document",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspace.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(32), server_default="upload", nullable=False),
        sa.Column("external_uri", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_source_document_workspace_id", "source_document", ["workspace_id"])
    op.create_table(
        "document_version",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_document_id",
            sa.Uuid(),
            sa.ForeignKey("source_document.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("plain_text", sa.Text(), nullable=False),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("source_document_id", "sha256", name="uq_version_source_hash"),
        sa.UniqueConstraint(
            "source_document_id", "version_number", name="uq_version_source_number"
        ),
        sa.CheckConstraint("version_number > 0", name="ck_version_number_positive"),
    )
    op.create_table(
        "source_chunk",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_version_id",
            sa.Uuid(),
            sa.ForeignKey("document_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column(
            "search_vector",
            TSVECTOR(),
            sa.Computed("to_tsvector('english'::regconfig, text)", persisted=True),
            nullable=False,
        ),
        sa.UniqueConstraint("document_version_id", "ordinal", name="uq_chunk_version_ordinal"),
        sa.CheckConstraint("ordinal >= 0", name="ck_chunk_ordinal_nonnegative"),
        sa.CheckConstraint(
            "start_char >= 0 AND end_char > start_char "
            "AND char_length(text) = end_char - start_char",
            name="ck_chunk_span",
        ),
    )
    op.create_index(
        "ix_source_chunk_search_vector", "source_chunk", ["search_vector"], postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_table("source_chunk")
    op.drop_table("document_version")
    op.drop_table("source_document")
    op.drop_table("workspace")

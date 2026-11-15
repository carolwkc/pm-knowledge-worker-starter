"""Keep derived local embeddings separate from immutable source evidence."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "chunk_embedding",
        sa.Column(
            "chunk_id",
            sa.Uuid(),
            sa.ForeignKey("source_chunk.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("model_id", sa.String(200), primary_key=True),
        sa.Column("embedding", Vector(384), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("chunk_embedding")
    # The extension may serve other schemas/applications; do not drop it.

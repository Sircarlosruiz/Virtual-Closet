"""create media_items table

Revision ID: a2b3c4d5e6f7
Revises: f7a8b9c0d1e2
Create Date: 2026-05-31 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("minio_key", sa.String(512), unique=True, nullable=False),
        sa.Column("media_type", sa.String(50), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_media_items_mayorista", "media_items", ["mayorista_id"])
    op.create_index("idx_media_items_mayorista_created", "media_items", ["mayorista_id", "created_at"])
    op.create_index("idx_media_items_type", "media_items", ["media_type"])


def downgrade() -> None:
    op.drop_index("idx_media_items_type", table_name="media_items")
    op.drop_index("idx_media_items_mayorista_created", table_name="media_items")
    op.drop_index("idx_media_items_mayorista", table_name="media_items")
    op.drop_table("media_items")

"""create garment_photos and model_photos tables

Revision ID: a1b2c3d4e5f7
Revises: c8d9e0f1a2b3
Create Date: 2026-05-26 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "garment_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("minio_key", sa.String(512), unique=True, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer, sa.CheckConstraint("size_bytes > 0"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_garment_photos_mayorista", "garment_photos", ["mayorista_id"])
    op.create_index("idx_garment_photos_mayorista_created", "garment_photos", ["mayorista_id", "uploaded_at"])

    op.create_table(
        "model_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="SET NULL"), nullable=True),
        sa.Column("minio_key", sa.String(512), unique=True, nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("is_curated", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer, sa.CheckConstraint("size_bytes > 0"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_model_photos_mayorista", "model_photos", ["mayorista_id"])
    op.create_index("idx_model_photos_curated", "model_photos", ["is_curated"])


def downgrade() -> None:
    op.drop_index("idx_model_photos_curated", table_name="model_photos")
    op.drop_index("idx_model_photos_mayorista", table_name="model_photos")
    op.drop_table("model_photos")
    op.drop_index("idx_garment_photos_mayorista_created", table_name="garment_photos")
    op.drop_index("idx_garment_photos_mayorista", table_name="garment_photos")
    op.drop_table("garment_photos")

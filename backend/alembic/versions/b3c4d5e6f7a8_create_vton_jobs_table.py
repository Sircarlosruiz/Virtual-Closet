"""create vton_jobs table

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f7
Create Date: 2026-05-26 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vton_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("garment_photo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("garment_photos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_photo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_photos.id", ondelete="SET NULL"), nullable=False),
        sa.Column("cloth_type", sa.String(20), sa.CheckConstraint("cloth_type IN ('upper_body', 'lower_body', 'dress')"), nullable=False),
        sa.Column("status", sa.String(20), sa.CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed')"), nullable=False, server_default="queued"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("error_reason", sa.Text, nullable=True),
        sa.Column("result_minio_key", sa.String(512), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_vton_jobs_mayorista", "vton_jobs", ["mayorista_id"])
    op.create_index("idx_vton_jobs_mayorista_created", "vton_jobs", ["mayorista_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_vton_jobs_mayorista_created", table_name="vton_jobs")
    op.drop_index("idx_vton_jobs_mayorista", table_name="vton_jobs")
    op.drop_table("vton_jobs")

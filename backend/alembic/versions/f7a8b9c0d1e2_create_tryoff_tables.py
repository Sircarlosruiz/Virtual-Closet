"""create tryoff tables

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-05-31 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tryoff_source_images table
    op.create_table(
        "tryoff_source_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("minio_key", sa.String(512), unique=True, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_tryoff_source_images_mayorista", "tryoff_source_images", ["mayorista_id"])
    op.create_index("idx_tryoff_source_images_mayorista_created", "tryoff_source_images", ["mayorista_id", "uploaded_at"])

    # Create tryoff_jobs table
    op.create_table(
        "tryoff_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tryoff_source_images.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("garment_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="2"),
        sa.Column("error_reason", sa.Text, nullable=True),
        sa.Column("output_minio_key", sa.String(512), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_tryoff_jobs_mayorista", "tryoff_jobs", ["mayorista_id"])
    op.create_index("idx_tryoff_jobs_mayorista_created", "tryoff_jobs", ["mayorista_id", "created_at"])
    op.create_index("idx_tryoff_jobs_source_image", "tryoff_jobs", ["source_image_id"])

    # Add check constraints
    op.create_check_constraint(
        "ck_tryoff_jobs_garment_type",
        "tryoff_jobs",
        "garment_type IN ('upper', 'lower', 'dress')"
    )
    op.create_check_constraint(
        "ck_tryoff_jobs_status",
        "tryoff_jobs",
        "status IN ('pending', 'processing', 'complete', 'failed')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_tryoff_jobs_status", "tryoff_jobs", type_="check")
    op.drop_constraint("ck_tryoff_jobs_garment_type", "tryoff_jobs", type_="check")
    op.drop_index("idx_tryoff_jobs_source_image", table_name="tryoff_jobs")
    op.drop_index("idx_tryoff_jobs_mayorista_created", table_name="tryoff_jobs")
    op.drop_index("idx_tryoff_jobs_mayorista", table_name="tryoff_jobs")
    op.drop_table("tryoff_jobs")
    op.drop_index("idx_tryoff_source_images_mayorista_created", table_name="tryoff_source_images")
    op.drop_index("idx_tryoff_source_images_mayorista", table_name="tryoff_source_images")
    op.drop_table("tryoff_source_images")

"""add_batch_job_tables

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-04 00:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create batch_jobs table first (batch_items depends on it)
    op.create_table(
        "batch_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("total_items", sa.Integer, nullable=False),
        sa.Column("completed_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("failed_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'in-progress', 'complete', 'partial', 'failed')", name="ck_batch_jobs_status"),
        sa.CheckConstraint("total_items >= 1 AND total_items <= 100", name="ck_batch_jobs_total_items"),
        sa.CheckConstraint("completed_count + failed_count <= total_items", name="ck_batch_jobs_counters"),
    )
    op.create_index("idx_batch_jobs_mayorista", "batch_jobs", ["mayorista_id"])
    op.create_index("idx_batch_jobs_mayorista_created", "batch_jobs", ["mayorista_id", "created_at"])

    # Create batch_items table (vton_jobs FK depends on it)
    op.create_table(
        "batch_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("batch_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("garment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cloth_type", sa.String(20), nullable=False),
        sa.Column("vton_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vton_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("media_save_error", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("result_media_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("cloth_type IN ('upper_body', 'lower_body', 'dress')", name="ck_batch_items_cloth_type"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'complete', 'failed')", name="ck_batch_items_status"),
    )
    op.create_index("idx_batch_items_batch", "batch_items", ["batch_id"])
    op.create_index("idx_batch_items_vton_job", "batch_items", ["vton_job_id"], postgresql_where="vton_job_id IS NOT NULL")

    # Add batch_item_id FK to vton_jobs (ADR-006: backwards-compatible)
    op.add_column(
        "vton_jobs",
        sa.Column(
            "batch_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_vton_jobs_batch_item_id",
        "vton_jobs",
        "batch_items",
        ["batch_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_vton_jobs_batch_item",
        "vton_jobs",
        ["batch_item_id"],
    )

    # Add vton_job_id unique constraint to media_items (ADR-010)
    op.add_column(
        "media_items",
        sa.Column("vton_job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint("uq_media_items_vton_job", "media_items", ["vton_job_id"])
    op.create_index("idx_media_items_vton_job", "media_items", ["vton_job_id"])


def downgrade() -> None:
    op.drop_index("idx_media_items_vton_job", table_name="media_items")
    op.drop_constraint("uq_media_items_vton_job", "media_items", type_="unique")
    op.drop_column("media_items", "vton_job_id")

    op.drop_index("idx_vton_jobs_batch_item", table_name="vton_jobs")
    op.drop_constraint("fk_vton_jobs_batch_item_id", "vton_jobs", type_="foreignkey")
    op.drop_column("vton_jobs", "batch_item_id")

    op.drop_index("idx_batch_items_vton_job", table_name="batch_items")
    op.drop_index("idx_batch_items_batch", table_name="batch_items")
    op.drop_table("batch_items")

    op.drop_index("idx_batch_jobs_mayorista_created", table_name="batch_jobs")
    op.drop_index("idx_batch_jobs_mayorista", table_name="batch_jobs")
    op.drop_table("batch_jobs")

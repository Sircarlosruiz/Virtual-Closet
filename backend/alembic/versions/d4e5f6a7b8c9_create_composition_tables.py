"""create product_overlays and composition_versions tables

Revision ID: d4e5f6a7b8c9
Revises: 9c0d1e2f3a4b
Create Date: 2026-09-17 22:44:11.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "9c0d1e2f3a4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_overlays",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "generation_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "composition_snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("composition_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("base_image_key", sa.Text, nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "generation_job_id", name="uq_product_overlays_generation_job_id"
        ),
    )
    op.create_index("idx_product_overlays_created_by", "product_overlays", ["created_by"])

    op.create_table(
        "composition_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "overlay_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_overlays.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("sku_normalized", sa.Text, nullable=False),
        sa.Column("placement", postgresql.JSONB, nullable=False),
        sa.Column("style", postgresql.JSONB, nullable=False),
        sa.Column("spec_hash", sa.String(64), nullable=False),
        sa.Column("font_version", sa.String(120), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("rendered_key", sa.Text, nullable=True),
        sa.Column("rendered_checksum", sa.String(80), nullable=True),
        sa.Column("fit_result", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "overlay_id", "version", name="uq_composition_versions_overlay_version"
        ),
        sa.UniqueConstraint(
            "overlay_id", "spec_hash", name="uq_composition_versions_overlay_spec_hash"
        ),
        sa.CheckConstraint(
            "status IN ('valid', 'blocked')", name="ck_composition_versions_status"
        ),
    )
    op.create_index(
        "idx_composition_versions_overlay_id", "composition_versions", ["overlay_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "idx_composition_versions_overlay_id", table_name="composition_versions"
    )
    op.drop_table("composition_versions")
    op.drop_index("idx_product_overlays_created_by", table_name="product_overlays")
    op.drop_table("product_overlays")

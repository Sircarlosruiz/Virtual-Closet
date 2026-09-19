"""create photoshoot aggregate tables

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-09-19 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photoshoots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "product_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_links.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "staff_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_image_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bridge_source_images.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mayorista_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("input_kind", sa.String(32), nullable=False),
        sa.Column("configuration", postgresql.JSONB, nullable=False),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="queued"
        ),
        sa.Column("expected_results", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("payload_fingerprint", sa.String(64), nullable=True),
        sa.Column("variant_key", sa.String(255), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "input_kind IN ('garment_on_model', 'flat_garment')",
            name="ck_photoshoots_input_kind",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'partial', 'completed', 'failed')",
            name="ck_photoshoots_status",
        ),
        sa.CheckConstraint("expected_results > 0", name="ck_photoshoots_expected"),
    )
    op.create_index(
        "ix_photoshoots_owned",
        "photoshoots",
        ["tenant_id", "product_link_id", "id"],
    )
    op.create_index(
        "ix_photoshoots_link_status",
        "photoshoots",
        ["product_link_id", "status"],
    )
    op.create_index("ix_photoshoots_source", "photoshoots", ["source_image_id"])

    op.create_table(
        "photoshoot_stages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "photoshoot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("photoshoots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="pending"
        ),
        sa.Column("external_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "external_refs",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("photoshoot_id", "name", name="uq_photoshoot_stages_name"),
        sa.CheckConstraint(
            "name IN ('tryoff', 'vton', 'poses', 'composition')",
            name="ck_photoshoot_stages_name",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'skipped', 'completed', 'failed')",
            name="ck_photoshoot_stages_status",
        ),
    )

    op.create_table(
        "photoshoot_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "photoshoot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("photoshoots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "generation_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("models.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "pose_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_photos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("variant_key", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("generation_job_id", name="uq_photoshoot_results_job"),
        sa.UniqueConstraint(
            "photoshoot_id",
            "model_id",
            "pose_id",
            name="uq_photoshoot_results_slot",
        ),
    )


def downgrade() -> None:
    op.drop_table("photoshoot_results")
    op.drop_table("photoshoot_stages")
    op.drop_index("ix_photoshoots_source", table_name="photoshoots")
    op.drop_index("ix_photoshoots_link_status", table_name="photoshoots")
    op.drop_index("ix_photoshoots_owned", table_name="photoshoots")
    op.drop_table("photoshoots")

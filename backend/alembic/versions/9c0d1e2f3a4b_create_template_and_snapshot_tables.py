"""create image_templates, template_references, and composition_snapshots tables

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-09-17 18:41:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9c0d1e2f3a4b"
down_revision: Union[str, None] = "8b9c0d1e2f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "image_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("scope", sa.String(10), nullable=False),
        sa.Column(
            "wholesaler_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(10), nullable=False, server_default="draft"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("background", sa.Text, nullable=True),
        sa.Column("colors", postgresql.JSONB, nullable=True),
        sa.Column("rack", sa.Text, nullable=True),
        sa.Column("prompt", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("scope IN ('common', 'private')", name="ck_image_templates_scope"),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')", name="ck_image_templates_status"
        ),
        sa.CheckConstraint(
            "(scope = 'private' AND wholesaler_id IS NOT NULL) "
            "OR (scope = 'common' AND wholesaler_id IS NULL)",
            name="ck_image_templates_scope_wholesaler",
        ),
    )
    op.create_index("idx_image_templates_scope", "image_templates", ["scope"])
    op.create_index("idx_image_templates_wholesaler_id", "image_templates", ["wholesaler_id"])

    op.create_table(
        "template_references",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("image_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.Text, nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_template_references_template_id", "template_references", ["template_id"]
    )

    op.create_table(
        "composition_snapshots",
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
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("image_templates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("template_version", sa.Integer, nullable=False),
        sa.Column("effective_configuration", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "generation_job_id", name="uq_composition_snapshots_generation_job_id"
        ),
    )
    op.create_index(
        "idx_composition_snapshots_template_id", "composition_snapshots", ["template_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "idx_composition_snapshots_template_id", table_name="composition_snapshots"
    )
    op.drop_table("composition_snapshots")

    op.drop_index("idx_template_references_template_id", table_name="template_references")
    op.drop_table("template_references")

    op.drop_index("idx_image_templates_wholesaler_id", table_name="image_templates")
    op.drop_index("idx_image_templates_scope", table_name="image_templates")
    op.drop_table("image_templates")

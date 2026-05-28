"""create catalogo and catalogo_item tables

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-05-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalogo",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "mayorista_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            sa.CheckConstraint(
                "status IN ('draft', 'published')", name="ck_catalogo_status"
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("item_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_catalogo_mayorista", "catalogo", ["mayorista_id"])
    op.create_index(
        "idx_catalogo_mayorista_created", "catalogo", ["mayorista_id", "created_at"]
    )

    op.create_table(
        "catalogo_item",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "catalog_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalogo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vton_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vton_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("garment_name", sa.String(200), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "cloth_type",
            sa.String(20),
            sa.CheckConstraint(
                "cloth_type IN ('upper_body', 'lower_body', 'dress')",
                name="ck_catalogo_item_cloth_type",
            ),
            nullable=False,
        ),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("image_key", sa.String(512), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "catalog_id", "position", name="uq_catalogo_item_position"
        ),
    )
    op.create_index(
        "idx_catalogo_item_catalog", "catalogo_item", ["catalog_id"]
    )
    op.create_index(
        "idx_catalogo_item_catalog_position",
        "catalogo_item",
        ["catalog_id", "position"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_catalogo_item_catalog_position", table_name="catalogo_item"
    )
    op.drop_index("idx_catalogo_item_catalog", table_name="catalogo_item")
    op.drop_table("catalogo_item")
    op.drop_index("idx_catalogo_mayorista_created", table_name="catalogo")
    op.drop_index("idx_catalogo_mayorista", table_name="catalogo")
    op.drop_table("catalogo")

"""create bridge_source_images table

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-19 01:50:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bridge_source_images",
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
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("declared_content_type", sa.String(50), nullable=False),
        sa.Column("declared_size_bytes", sa.Integer, nullable=False),
        sa.Column("actual_content_type", sa.String(50), nullable=True),
        sa.Column("actual_size_bytes", sa.Integer, nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column(
            "registered_media_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("registered_media_kind", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "storage_key", name="uq_bridge_source_images_storage_key"
        ),
        sa.CheckConstraint(
            "kind IN ('garment_on_model', 'flat_garment')",
            name="ck_bridge_source_images_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'ready', 'rejected')",
            name="ck_bridge_source_images_status",
        ),
        sa.CheckConstraint(
            "declared_content_type IN ('image/jpeg', 'image/png')",
            name="ck_bridge_source_images_declared_type",
        ),
        sa.CheckConstraint(
            "declared_size_bytes > 0",
            name="ck_bridge_source_images_declared_size",
        ),
    )
    op.create_index(
        "ix_bridge_source_images_staff_id",
        "bridge_source_images",
        ["staff_id"],
    )
    op.create_index(
        "ix_bridge_source_images_owned",
        "bridge_source_images",
        ["tenant_id", "product_link_id", "id"],
    )
    op.create_index(
        "ix_bridge_source_images_link_status",
        "bridge_source_images",
        ["product_link_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bridge_source_images_link_status",
        table_name="bridge_source_images",
    )
    op.drop_index(
        "ix_bridge_source_images_owned",
        table_name="bridge_source_images",
    )
    op.drop_index(
        "ix_bridge_source_images_staff_id",
        table_name="bridge_source_images",
    )
    op.drop_table("bridge_source_images")

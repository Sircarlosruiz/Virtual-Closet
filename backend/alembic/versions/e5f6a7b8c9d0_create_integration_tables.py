"""create service_clients and product_links tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-18 15:18:43.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_clients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("system", sa.String(40), nullable=False),
        sa.Column("secret_hash", sa.Text, nullable=False),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_service_clients_tenant_id", "service_clients", ["tenant_id"])
    op.create_index("idx_service_clients_system", "service_clients", ["system"])

    op.create_table(
        "product_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("system", sa.String(40), nullable=False),
        sa.Column("external_product_id", sa.String(255), nullable=False),
        sa.Column("external_wholesaler_id", sa.String(255), nullable=True),
        sa.Column(
            "mayorista_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prenda_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prenda.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "system",
            "external_product_id",
            name="uq_product_links_system_external_product",
        ),
    )
    op.create_index("ix_product_links_mayorista_id", "product_links", ["mayorista_id"])
    op.create_index("ix_product_links_tenant_id", "product_links", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_product_links_tenant_id", table_name="product_links")
    op.drop_index("ix_product_links_mayorista_id", table_name="product_links")
    op.drop_table("product_links")
    op.drop_index("idx_service_clients_system", table_name="service_clients")
    op.drop_index("ix_service_clients_tenant_id", table_name="service_clients")
    op.drop_table("service_clients")

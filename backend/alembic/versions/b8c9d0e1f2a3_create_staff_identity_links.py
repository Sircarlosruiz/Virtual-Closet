"""create staff_identity_links table

Revision ID: b8c9d0e1f2a3
Revises: f6a7b8c9d0e1
Create Date: 2026-09-19 00:40:02.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_identity_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("system", sa.String(40), nullable=False),
        sa.Column("external_staff_id", sa.String(255), nullable=False),
        sa.Column(
            "mayorista_id",
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
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "system",
            "external_staff_id",
            name="uq_staff_identity_links_system_external_staff",
        ),
    )
    op.create_index(
        "ix_staff_identity_links_mayorista_id",
        "staff_identity_links",
        ["mayorista_id"],
    )
    op.create_index(
        "ix_staff_identity_links_tenant_id",
        "staff_identity_links",
        ["tenant_id"],
    )
    op.create_index(
        "ix_staff_identity_links_tenant_mayorista",
        "staff_identity_links",
        ["tenant_id", "mayorista_id"],
    )
    op.create_index(
        "ix_staff_identity_links_tenant_active",
        "staff_identity_links",
        ["tenant_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staff_identity_links_tenant_active",
        table_name="staff_identity_links",
    )
    op.drop_index(
        "ix_staff_identity_links_tenant_mayorista",
        table_name="staff_identity_links",
    )
    op.drop_index(
        "ix_staff_identity_links_tenant_id",
        table_name="staff_identity_links",
    )
    op.drop_index(
        "ix_staff_identity_links_mayorista_id",
        table_name="staff_identity_links",
    )
    op.drop_table("staff_identity_links")

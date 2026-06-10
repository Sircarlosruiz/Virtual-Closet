"""add role column to mayorista + create refresh_tokens table

Revision ID: a9b8c7d6e5f4
Revises: 1a2b3c4d5e6f
Create Date: 2026-06-09 19:45:00.000000

This migration:
1. Adds `role` column to `mayorista` table (default: 'mayorista')
2. Creates `refresh_tokens` table for session management
"""

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "a9b8c7d6e5f4"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add role column to mayorista
    op.add_column(
        "mayorista",
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default="mayorista",
        ),
    )

    # Step 2: Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "mayorista_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("jti", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
    )

    # Step 3: Add indexes for admin listing
    op.create_index(
        "idx_mayorista_tenant_role",
        "mayorista",
        ["tenant_id", "role"],
    )


def downgrade() -> None:
    op.drop_index("idx_mayorista_tenant_role", table_name="mayorista")
    op.drop_table("refresh_tokens")
    op.drop_column("mayorista", "role")

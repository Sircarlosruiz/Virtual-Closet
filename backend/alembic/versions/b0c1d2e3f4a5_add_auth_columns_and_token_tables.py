"""add email_verified, is_locked, failed_attempts to mayorista + create email_verification_tokens and unlock_tokens tables

Revision ID: b0c1d2e3f4a5
Revises: a9b8c7d6e5f4
Create Date: 2026-06-10 00:00:00.000000

This migration:
1. Adds email_verified, is_locked, failed_attempts, updated_at to mayorista
2. Backfills existing mayoristas as email_verified=true
3. Creates email_verification_tokens table
4. Creates unlock_tokens table
"""

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "b0c1d2e3f4a5"
down_revision = "a9b8c7d6e5f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add auth columns to mayorista
    op.add_column(
        "mayorista",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "mayorista",
        sa.Column(
            "is_locked",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "mayorista",
        sa.Column(
            "failed_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "mayorista",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Step 2: Backfill existing mayoristas as verified
    op.execute(
        "UPDATE mayorista SET email_verified = true WHERE email_verified = false"
    )

    # Step 3: Create email_verification_tokens table
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("token", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Partial index for unused tokens
    op.create_index(
        "idx_email_verification_user_unused",
        "email_verification_tokens",
        ["user_id"],
        postgresql_where=sa.text("used = false"),
    )

    # Step 4: Create unlock_tokens table
    op.create_table(
        "unlock_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("token", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Partial index for unused tokens
    op.create_index(
        "idx_unlock_user_unused",
        "unlock_tokens",
        ["user_id"],
        postgresql_where=sa.text("used = false"),
    )


def downgrade() -> None:
    op.drop_index("idx_unlock_user_unused", table_name="unlock_tokens")
    op.drop_table("unlock_tokens")
    op.drop_index("idx_email_verification_user_unused", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_column("mayorista", "updated_at")
    op.drop_column("mayorista", "failed_attempts")
    op.drop_column("mayorista", "is_locked")
    op.drop_column("mayorista", "email_verified")

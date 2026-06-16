"""add password_reset_tokens table

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-10 00:00:00.000000

This migration creates the password_reset_tokens table for password
recovery via single-use, time-limited email links.
"""

import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Create password_reset_tokens table."""

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("mayorista_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(60), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_password_reset_tokens_mayorista_unused",
        "password_reset_tokens",
        ["mayorista_id", "used"],
    )


def downgrade() -> None:
    """Drop password_reset_tokens table."""
    op.drop_index("idx_password_reset_tokens_mayorista_unused", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

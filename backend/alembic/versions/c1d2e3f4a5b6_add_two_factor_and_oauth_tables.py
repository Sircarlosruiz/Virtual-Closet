"""add two_factor_configs, backup_codes, sms_otp_records, oauth_links tables

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-06-10 00:00:00.000000

This migration creates tables for:
1. two_factor_configs — per-user 2FA configuration (TOTP/SMS)
2. backup_codes — single-use backup recovery codes
3. sms_otp_records — active SMS OTP records
4. oauth_links — external OAuth identity links (Google)
"""

import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision = "b0c1d2e3f4a5"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Create 2FA and OAuth tables."""

    # ── two_factor_configs ─────────────────────────────────────────────
    op.create_table(
        "two_factor_configs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("mayorista_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("method", sa.String(4), nullable=False, server_default="totp"),
        sa.Column("totp_secret_encrypted", sa.Text, nullable=True),
        sa.Column("phone_number_encrypted", sa.Text, nullable=True),
        sa.Column("is_configured", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("backup_codes_remaining", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint("method IN ('totp', 'sms')", name="ck_two_factor_config_method"),
    )
    op.create_index("idx_two_factor_config_mayorista", "two_factor_configs", ["mayorista_id"])

    # ── backup_codes ───────────────────────────────────────────────────
    op.create_table(
        "backup_codes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("mayorista_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(60), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_backup_codes_mayorista_unused", "backup_codes", ["mayorista_id", "used"])

    # ── sms_otp_records ────────────────────────────────────────────────
    op.create_table(
        "sms_otp_records",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("mayorista_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("otp_hash", sa.String(60), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_sms_otp_mayorista", "sms_otp_records", ["mayorista_id"])

    # ── oauth_links ────────────────────────────────────────────────────
    op.create_table(
        "oauth_links",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("mayorista_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(10), nullable=False, server_default="google"),
        sa.Column("provider_sub", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(255), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_sub", name="uq_oauth_link_provider_sub"),
    )
    op.create_index("idx_oauth_links_mayorista", "oauth_links", ["mayorista_id"])
    op.create_index("idx_oauth_links_provider_sub", "oauth_links", ["provider", "provider_sub"])


def downgrade() -> None:
    """Drop 2FA and OAuth tables."""
    op.drop_index("idx_oauth_links_provider_sub", table_name="oauth_links")
    op.drop_index("idx_oauth_links_mayorista", table_name="oauth_links")
    op.drop_table("oauth_links")

    op.drop_index("idx_sms_otp_mayorista", table_name="sms_otp_records")
    op.drop_table("sms_otp_records")

    op.drop_index("idx_backup_codes_mayorista_unused", table_name="backup_codes")
    op.drop_table("backup_codes")

    op.drop_index("idx_two_factor_config_mayorista", table_name="two_factor_configs")
    op.drop_table("two_factor_configs")

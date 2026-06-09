"""multi-tenancy: tenants table + tenant_id backfill + FK constraints

This is a multi-step migration that introduces multi-tenancy to the platform.

Steps:
1. Create `tenants` table
2. Insert default tenant for existing data
3. Add nullable `tenant_id` to `mayorista`, `media_items`, `catalogo`, `vton_jobs`, `batch_jobs`
4. Backfill existing rows with default tenant
5. Add NOT NULL constraint on `tenant_id` columns
6. Add FK constraints referencing `tenants(id)`
7. Add indexes on `tenant_id` for query performance

IMPORTANT: This migration runs in a single transaction. If any step fails,
the entire migration rolls back.

Revision ID: 1a2b3c4d5e6f
Revises: 0c2cff14de00
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = '0c2cff14de00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"

# Tables that need tenant_id backfill
PLATFORM_TABLES = [
    "mayorista",
    "media_items",
    "catalogo",
    "vton_jobs",
    "batch_jobs",
]


def upgrade() -> None:
    """Upgrade schema with multi-tenancy support."""

    # Step 1: Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("buyer_link_secret", sa.String(64), nullable=False),
        sa.Column("settings", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # Step 2: Insert default tenant for existing data
    op.execute(
        sa.text("""
            INSERT INTO tenants (id, name, slug, buyer_link_secret, settings, is_active)
            VALUES (
                :tenant_id,
                'Default',
                'default',
                gen_random_uuid()::text,
                '{}',
                true
            )
            ON CONFLICT (id) DO NOTHING
        """).bindparams(tenant_id=DEFAULT_TENANT_ID)
    )

    # Step 3: Add nullable tenant_id to platform tables
    for table in PLATFORM_TABLES:
        op.add_column(
            table,
            sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        )

    # Step 4: Backfill existing rows with default tenant
    for table in PLATFORM_TABLES:
        op.execute(
            sa.text(f"""
                UPDATE {table}
                SET tenant_id = :tenant_id
                WHERE tenant_id IS NULL
            """).bindparams(tenant_id=DEFAULT_TENANT_ID)
        )

    # Step 5: Add NOT NULL constraint on tenant_id columns
    for table in PLATFORM_TABLES:
        op.alter_column(
            table,
            "tenant_id",
            nullable=False,
        )

    # Step 6: Add FK constraints
    for table in PLATFORM_TABLES:
        op.create_foreign_key(
            f"fk_{table}_tenant",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
        )

    # Step 7: Add indexes on tenant_id for query performance
    for table in PLATFORM_TABLES:
        op.create_index(
            f"ix_{table}_tenant_id",
            table,
            ["tenant_id"],
        )


def downgrade() -> None:
    """Downgrade schema: remove tenant_id columns and tenants table."""

    # Drop indexes
    for table in PLATFORM_TABLES:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)

    # Drop FK constraints
    for table in PLATFORM_TABLES:
        op.drop_constraint(f"fk_{table}_tenant", table, type_="foreignkey")

    # Drop tenant_id columns
    for table in PLATFORM_TABLES:
        op.drop_column(table, "tenant_id")

    # Drop tenants table
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")

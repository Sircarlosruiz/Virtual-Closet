"""create provider-neutral image generation jobs

Revision ID: 7a8b9c0d1e2f
Revises: 26643529af50
Create Date: 2026-09-17 02:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7a8b9c0d1e2f"
down_revision: Union[str, None] = "26643529af50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mayorista.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("input_data", postgresql.JSONB, nullable=False),
        sa.Column("result_key", sa.Text, nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "mode IN ('try_on', 'text', 'edit', 'extraction')",
            name="ck_generation_jobs_mode",
        ),
        sa.CheckConstraint(
            "provider IN ('openai', 'vton')",
            name="ck_generation_jobs_provider",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_generation_jobs_status",
        ),
    )
    op.create_index("idx_generation_jobs_owner_id", "generation_jobs", ["owner_id"])
    op.create_index("idx_generation_jobs_status", "generation_jobs", ["status"])
    op.create_index(
        "idx_generation_jobs_owner_created",
        "generation_jobs",
        ["owner_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_generation_jobs_owner_created", table_name="generation_jobs")
    op.drop_index("idx_generation_jobs_status", table_name="generation_jobs")
    op.drop_index("idx_generation_jobs_owner_id", table_name="generation_jobs")
    op.drop_table("generation_jobs")

"""add provider invocation history, idempotency, lease, and usage columns

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-09-17 17:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8b9c0d1e2f3a"
down_revision: Union[str, None] = "7a8b9c0d1e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generation_jobs", sa.Column("idempotency_key", sa.String(255), nullable=True))
    op.add_column(
        "generation_jobs", sa.Column("payload_fingerprint", sa.String(64), nullable=True)
    )
    op.add_column(
        "generation_jobs",
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("lock_token", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("usage_status", sa.String(20), nullable=False, server_default="unknown"),
    )
    op.add_column("generation_jobs", sa.Column("usage_model", sa.String(80), nullable=True))
    op.add_column(
        "generation_jobs", sa.Column("usage_call_count", sa.Integer, nullable=True)
    )
    op.create_unique_constraint(
        "uq_generation_jobs_idempotency",
        "generation_jobs",
        ["idempotency_key", "payload_fingerprint"],
    )

    op.create_table(
        "provider_invocations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer, nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model", sa.String(80), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_category", sa.String(20), nullable=True),
        sa.Column("retryable", sa.Boolean, nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("usage_model", sa.String(80), nullable=True),
        sa.Column("usage_call_count", sa.Integer, nullable=True),
        sa.Column("usage_raw", postgresql.JSONB, nullable=True),
        sa.UniqueConstraint(
            "job_id", "attempt_number", name="uq_provider_invocations_job_attempt"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'timed_out')",
            name="ck_provider_invocations_status",
        ),
        sa.CheckConstraint(
            "error_category IS NULL OR error_category IN ('transient', 'terminal')",
            name="ck_provider_invocations_error_category",
        ),
        sa.CheckConstraint(
            "usage_status IN ('reported', 'unknown')",
            name="ck_provider_invocations_usage_status",
        ),
    )
    op.create_index("idx_provider_invocations_job_id", "provider_invocations", ["job_id"])
    op.create_index("idx_provider_invocations_status", "provider_invocations", ["status"])


def downgrade() -> None:
    op.drop_index("idx_provider_invocations_status", table_name="provider_invocations")
    op.drop_index("idx_provider_invocations_job_id", table_name="provider_invocations")
    op.drop_table("provider_invocations")

    op.drop_constraint(
        "uq_generation_jobs_idempotency", "generation_jobs", type_="unique"
    )
    op.drop_column("generation_jobs", "usage_call_count")
    op.drop_column("generation_jobs", "usage_model")
    op.drop_column("generation_jobs", "usage_status")
    op.drop_column("generation_jobs", "locked_at")
    op.drop_column("generation_jobs", "lock_token")
    op.drop_column("generation_jobs", "retry_count")
    op.drop_column("generation_jobs", "payload_fingerprint")
    op.drop_column("generation_jobs", "idempotency_key")

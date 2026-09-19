"""add queue wait and execution duration columns on generation_jobs

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-09-19 01:47:09.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs",
        sa.Column("concurrency_wait_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("provider_call_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("queue_wait_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("execution_seconds", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_jobs", "execution_seconds")
    op.drop_column("generation_jobs", "queue_wait_seconds")
    op.drop_column("generation_jobs", "provider_call_started_at")
    op.drop_column("generation_jobs", "concurrency_wait_started_at")

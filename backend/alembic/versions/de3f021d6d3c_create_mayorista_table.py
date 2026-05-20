"""create mayorista table

Revision ID: de3f021d6d3c
Revises:
Create Date: 2026-05-20 00:47:54.126236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "de3f021d6d3c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mayorista",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("nombre_negocio", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(10), nullable=False, server_default="base"),
        sa.Column("trial_activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "trial_expira_en",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now() + INTERVAL '30 days'"),
        ),
        sa.Column("whatsapp", sa.String(20), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_mayorista_email", "mayorista", ["email"])


def downgrade() -> None:
    op.drop_index("idx_mayorista_email", table_name="mayorista")
    op.drop_table("mayorista")

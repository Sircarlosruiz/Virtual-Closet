"""create modelo_ia table

Revision ID: a1b2c3d4e5f6
Revises: 4d14008659c2
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "4d14008659c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "modelo_ia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("thumbnail_key", sa.Text, nullable=False),
        sa.Column("plan_minimo", sa.String(10), nullable=False, server_default="base"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_modelo_ia_plan_minimo", "modelo_ia", ["plan_minimo"])


def downgrade() -> None:
    op.drop_index("idx_modelo_ia_plan_minimo", table_name="modelo_ia")
    op.drop_table("modelo_ia")

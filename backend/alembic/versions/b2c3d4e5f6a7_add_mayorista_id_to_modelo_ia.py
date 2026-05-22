"""add mayorista_id to modelo_ia table

Revision ID: b2c3d4e5f6a7
Revises: f6e5d4c3b2a1
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f6e5d4c3b2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "modelo_ia",
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_modelo_ia_mayorista",
        "modelo_ia", "mayorista",
        ["mayorista_id"], ["id"],
    )
    op.create_index("idx_modelo_ia_mayorista", "modelo_ia", ["mayorista_id"])


def downgrade() -> None:
    op.drop_index("idx_modelo_ia_mayorista", table_name="modelo_ia")
    op.drop_constraint("fk_modelo_ia_mayorista", "modelo_ia", type_="foreignkey")
    op.drop_column("modelo_ia", "mayorista_id")

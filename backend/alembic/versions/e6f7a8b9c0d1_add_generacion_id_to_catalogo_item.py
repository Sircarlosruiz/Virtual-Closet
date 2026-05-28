"""add generacion_id to catalogo_item, nullable vton_job_id

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-05-28 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "catalogo_item",
        "vton_job_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "catalogo_item",
        sa.Column(
            "generacion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generacion.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_catalogo_item_source",
        "catalogo_item",
        "(vton_job_id IS NOT NULL) OR (generacion_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_catalogo_item_source", "catalogo_item", type_="check")
    op.drop_column("catalogo_item", "generacion_id")
    op.alter_column(
        "catalogo_item",
        "vton_job_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

"""create generacion table

Revision ID: f6e5d4c3b2a1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-20 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f6e5d4c3b2a1"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prenda_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prenda.id", ondelete="CASCADE"), nullable=False),
        sa.Column("modelo_ia_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("modelo_ia.id"), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("imagen_generada_key", sa.Text, nullable=True),
        sa.Column("thumbnail_key", sa.Text, nullable=True),
        sa.Column("costo_inferencia_usd", sa.Numeric(10, 4), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_generacion_mayorista_id", "generacion", ["mayorista_id"])
    op.create_index("idx_generacion_prenda_id", "generacion", ["prenda_id"])
    op.create_index("idx_generacion_estado", "generacion", ["estado"])
    op.create_index("idx_generacion_prenda_created", "generacion", ["prenda_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_generacion_prenda_created", table_name="generacion")
    op.drop_index("idx_generacion_estado", table_name="generacion")
    op.drop_index("idx_generacion_prenda_id", table_name="generacion")
    op.drop_index("idx_generacion_mayorista_id", table_name="generacion")
    op.drop_table("generacion")

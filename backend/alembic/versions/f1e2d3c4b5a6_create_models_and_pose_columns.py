"""create models table and extend model_photos with model_id and pose

Revision ID: f1e2d3c4b5a6
Revises: 0c2cff14de00
Create Date: 2026-07-18 04:10:25.000000

ADR-012: extend model_photos instead of a parallel pose-photo table.
Existing rows keep model_id = NULL and pose = NULL, so the new CHECK
constraints pass by construction.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, None] = "0c2cff14de00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_models_mayorista", "models", ["mayorista_id"])

    op.add_column(
        "model_photos",
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=True),
    )
    op.add_column(
        "model_photos",
        sa.Column("pose", sa.String(10), nullable=True),
    )
    op.create_index("idx_model_photos_model", "model_photos", ["model_id"])
    op.create_unique_constraint(
        "uq_model_photos_model_pose", "model_photos", ["model_id", "pose"]
    )
    op.create_check_constraint(
        "chk_model_photos_pose_values",
        "model_photos",
        "pose IN ('front', 'side', 'back')",
    )
    op.create_check_constraint(
        "chk_model_photos_model_pose_coupling",
        "model_photos",
        "(model_id IS NULL) = (pose IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("chk_model_photos_model_pose_coupling", "model_photos")
    op.drop_constraint("chk_model_photos_pose_values", "model_photos")
    op.drop_constraint("uq_model_photos_model_pose", "model_photos")
    op.drop_index("idx_model_photos_model", table_name="model_photos")
    op.drop_column("model_photos", "pose")
    op.drop_column("model_photos", "model_id")
    op.drop_index("idx_models_mayorista", table_name="models")
    op.drop_table("models")

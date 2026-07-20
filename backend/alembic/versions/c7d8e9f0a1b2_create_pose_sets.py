"""create pose_sets table

Revision ID: c7d8e9f0a1b2
Revises: b7c8d9e0f1a2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pose_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mayorista_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("garment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("garment_photos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("batch_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("batch_id", name="uq_pose_sets_batch_id"),
    )
    op.create_index("idx_pose_sets_mayorista_created", "pose_sets", ["mayorista_id", "created_at"])
    op.create_index("idx_pose_sets_tenant", "pose_sets", ["tenant_id"])
    op.create_index("idx_pose_sets_model", "pose_sets", ["model_id"])


def downgrade() -> None:
    op.drop_index("idx_pose_sets_model", table_name="pose_sets")
    op.drop_index("idx_pose_sets_tenant", table_name="pose_sets")
    op.drop_index("idx_pose_sets_mayorista_created", table_name="pose_sets")
    op.drop_table("pose_sets")

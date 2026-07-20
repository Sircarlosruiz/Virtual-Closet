import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from models.mayorista import Base


class PoseSet(Base):
    """Mayorista-owned grouping for one multi-pose batch submission."""

    __tablename__ = "pose_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id = Column(
        UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
    )
    garment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("garment_photos.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("batch_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("batch_id", name="uq_pose_sets_batch_id"),
        Index("idx_pose_sets_mayorista_created", "mayorista_id", "created_at"),
        Index("idx_pose_sets_tenant", "tenant_id"),
        Index("idx_pose_sets_model", "model_id"),
    )

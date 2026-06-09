import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class ClothType(enum.Enum):
    upper_body = "upper_body"
    lower_body = "lower_body"
    dress = "dress"


class JobStatus(enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class VTONJob(Base):
    """A single VTON generation request with full lifecycle tracking."""

    __tablename__ = "vton_jobs"

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
    garment_photo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("garment_photos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_photo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("model_photos.id", ondelete="SET NULL"),
        nullable=False,
    )
    cloth_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error_reason = Column(Text, nullable=True)
    result_minio_key = Column(String(512), unique=True, nullable=True)
    batch_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("batch_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    mayorista = relationship("Mayorista", back_populates="vton_jobs")
    tenant = relationship("Tenant", backref="vton_jobs")
    garment_photo = relationship("GarmentPhoto", foreign_keys=[garment_photo_id])
    model_photo = relationship("ModelPhoto", foreign_keys=[model_photo_id])
    batch_item = relationship("BatchItem", foreign_keys=[batch_item_id])

    __table_args__ = (
        CheckConstraint(
            "cloth_type IN ('upper_body', 'lower_body', 'dress')",
            name="ck_vton_jobs_cloth_type",
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_vton_jobs_status",
        ),
        Index("idx_vton_jobs_mayorista", "mayorista_id"),
        Index("idx_vton_jobs_tenant", "tenant_id"),
        Index("idx_vton_jobs_mayorista_created", "mayorista_id", "created_at"),
        Index("idx_vton_jobs_batch_item", "batch_item_id"),
    )

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class BatchJobStatus(enum.Enum):
    pending = "pending"
    in_progress = "in-progress"
    complete = "complete"
    partial = "partial"
    failed = "failed"


class BatchItemStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


BATCH_ITEM_CAP = 100


class BatchJob(Base):
    """Aggregate root for a named group of VTON pairings submitted by a mayorista."""

    __tablename__ = "batch_jobs"

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
    name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    total_items = Column(Integer, nullable=False)
    completed_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    mayorista = relationship("Mayorista", back_populates="batch_jobs")
    tenant = relationship("Tenant", backref="batch_jobs")
    items = relationship(
        "BatchItem", back_populates="batch", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in-progress', 'complete', 'partial', 'failed')",
            name="ck_batch_jobs_status",
        ),
        CheckConstraint(
            f"total_items >= 1 AND total_items <= {BATCH_ITEM_CAP}",
            name="ck_batch_jobs_total_items",
        ),
        CheckConstraint(
            "completed_count + failed_count <= total_items",
            name="ck_batch_jobs_counters",
        ),
        Index("idx_batch_jobs_mayorista", "mayorista_id"),
        Index("idx_batch_jobs_tenant", "tenant_id"),
        Index(
            "idx_batch_jobs_mayorista_created", "mayorista_id", "created_at", postgresql_ops={"created_at": "DESC"}
        ),
    )


class BatchItem(Base):
    """Individual garment+model pairing within a BatchJob."""

    __tablename__ = "batch_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("batch_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    garment_id = Column(UUID(as_uuid=True), nullable=False)
    model_id = Column(UUID(as_uuid=True), nullable=False)
    cloth_type = Column(String(20), nullable=False)
    vton_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vton_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    media_save_error = Column(Boolean, nullable=False, default=False)
    retry_count = Column(Integer, nullable=False, default=0)
    result_media_id = Column(
        UUID(as_uuid=True),
        ForeignKey("media_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    batch = relationship("BatchJob", back_populates="items")
    vton_job = relationship("VTONJob", foreign_keys=[vton_job_id])
    result_media = relationship("MediaItem", foreign_keys=[result_media_id])

    __table_args__ = (
        CheckConstraint(
            "cloth_type IN ('upper_body', 'lower_body', 'dress')",
            name="ck_batch_items_cloth_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'complete', 'failed')",
            name="ck_batch_items_status",
        ),
        Index("idx_batch_items_batch", "batch_id"),
        Index("idx_batch_items_vton_job", "vton_job_id", postgresql_where="vton_job_id IS NOT NULL"),
    )

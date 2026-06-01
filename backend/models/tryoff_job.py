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


class GarmentType(enum.Enum):
    upper = "upper"
    lower = "lower"
    dress = "dress"


class TryoffJobStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class SourceImage(Base):
    """A source image uploaded for TryOff garment extraction."""

    __tablename__ = "tryoff_source_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
    )
    minio_key = Column(String(512), unique=True, nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    mayorista = relationship("Mayorista", back_populates="tryoff_source_images")
    jobs = relationship("TryoffJob", back_populates="source_image")

    __table_args__ = (
        Index("idx_tryoff_source_images_mayorista", "mayorista_id"),
        Index("idx_tryoff_source_images_mayorista_created", "mayorista_id", "uploaded_at"),
    )


class TryoffJob(Base):
    """A single TryOff garment extraction job with full lifecycle tracking."""

    __tablename__ = "tryoff_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tryoff_source_images.id", ondelete="RESTRICT"),
        nullable=False,
    )
    garment_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=2)
    error_reason = Column(Text, nullable=True)
    output_minio_key = Column(String(512), unique=True, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    mayorista = relationship("Mayorista", back_populates="tryoff_jobs")
    source_image = relationship("SourceImage", back_populates="jobs")

    __table_args__ = (
        CheckConstraint(
            "garment_type IN ('upper', 'lower', 'dress')",
            name="ck_tryoff_jobs_garment_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'complete', 'failed')",
            name="ck_tryoff_jobs_status",
        ),
        Index("idx_tryoff_jobs_mayorista", "mayorista_id"),
        Index("idx_tryoff_jobs_mayorista_created", "mayorista_id", "created_at"),
        Index("idx_tryoff_jobs_source_image", "source_image_id"),
    )

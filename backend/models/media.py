import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class GarmentPhoto(Base):
    """A garment photo uploaded by a mayorista for use as VTON input."""

    __tablename__ = "garment_photos"

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

    mayorista = relationship("Mayorista", back_populates="garment_photos")

    __table_args__ = (
        Index("idx_garment_photos_mayorista", "mayorista_id"),
        Index("idx_garment_photos_mayorista_created", "mayorista_id", "uploaded_at"),
    )


class ModelPhoto(Base):
    """A model photo — either uploaded by a mayorista or from the curated library."""

    __tablename__ = "model_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="SET NULL"),
        nullable=True,
    )
    minio_key = Column(String(512), unique=True, nullable=False)
    label = Column(String(255), nullable=False)
    is_curated = Column(Boolean, nullable=False, default=False)
    content_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    mayorista = relationship("Mayorista", back_populates="model_photos")

    __table_args__ = (
        Index("idx_model_photos_mayorista", "mayorista_id"),
        Index("idx_model_photos_curated", "is_curated"),
    )

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class GenerationJob(Base):
    """Durable, provider-neutral image generation request."""

    __tablename__ = "generation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode = Column(String(20), nullable=False)
    provider = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, server_default="queued")
    input_data = Column(JSONB, nullable=False)
    result_key = Column(Text, nullable=True)
    error_code = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    owner = relationship("Mayorista")

    __table_args__ = (
        Index("idx_generation_jobs_owner_id", "owner_id"),
        Index("idx_generation_jobs_status", "status"),
        Index("idx_generation_jobs_owner_created", "owner_id", "created_at"),
    )

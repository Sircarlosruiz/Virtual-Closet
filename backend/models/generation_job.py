import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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

    # Reliability extension (bolt 044): idempotency, concurrency lease, retry
    # count, and denormalized usage summary for the completing invocation.
    idempotency_key = Column(String(255), nullable=True)
    payload_fingerprint = Column(String(64), nullable=True)
    retry_count = Column(Integer, nullable=False, server_default="0")
    lock_token = Column(UUID(as_uuid=True), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    usage_status = Column(String(20), nullable=False, server_default="unknown")
    usage_model = Column(String(80), nullable=True)
    usage_call_count = Column(Integer, nullable=True)

    owner = relationship("Mayorista")
    invocations = relationship(
        "ProviderInvocation",
        back_populates="job",
        order_by="ProviderInvocation.attempt_number",
    )

    __table_args__ = (
        Index("idx_generation_jobs_owner_id", "owner_id"),
        Index("idx_generation_jobs_status", "status"),
        Index("idx_generation_jobs_owner_created", "owner_id", "created_at"),
        UniqueConstraint(
            "idempotency_key",
            "payload_fingerprint",
            name="uq_generation_jobs_idempotency",
        ),
    )

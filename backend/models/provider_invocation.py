import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class ProviderInvocation(Base):
    """One attempt to execute a GenerationJob against a provider.

    Append-only attempt history. Never stores a provider credential, raw
    request body, or raw response body — only sanitized, safe fields
    (ADR-047).
    """

    __tablename__ = "provider_invocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number = Column(Integer, nullable=False)
    provider = Column(String(20), nullable=False)
    model = Column(String(80), nullable=True)
    status = Column(String(20), nullable=False)
    error_code = Column(String(80), nullable=True)
    error_category = Column(String(20), nullable=True)
    retryable = Column(Boolean, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    usage_status = Column(String(20), nullable=False, server_default="unknown")
    usage_model = Column(String(80), nullable=True)
    usage_call_count = Column(Integer, nullable=True)
    usage_raw = Column(JSONB, nullable=True)

    job = relationship("GenerationJob", back_populates="invocations")

    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number", name="uq_provider_invocations_job_attempt"),
        Index("idx_provider_invocations_job_id", "job_id"),
        Index("idx_provider_invocations_status", "status"),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'timed_out')",
            name="ck_provider_invocations_status",
        ),
        CheckConstraint(
            "error_category IS NULL OR error_category IN ('transient', 'terminal')",
            name="ck_provider_invocations_error_category",
        ),
        CheckConstraint(
            "usage_status IN ('reported', 'unknown')",
            name="ck_provider_invocations_usage_status",
        ),
    )

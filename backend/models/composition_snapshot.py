import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from models.mayorista import Base


class CompositionSnapshot(Base):
    """Immutable, frozen configuration captured for one generation result.

    Insert-only: no update path is exposed. `generation_job_id` is unique so
    the database — not just application logic — enforces exactly one
    snapshot per generation job (ADR-052).
    """

    __tablename__ = "composition_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("image_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_version = Column(Integer, nullable=False)
    effective_configuration = Column(JSONB, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "generation_job_id", name="uq_composition_snapshots_generation_job_id"
        ),
        Index("idx_composition_snapshots_template_id", "template_id"),
    )

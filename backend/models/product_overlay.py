import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class ProductOverlay(Base):
    """Versioned SKU / fixed-element overlay attached to one generation result.

    Identified per generation result; new SKU/style configurations append a
    `CompositionVersion` rather than mutating an existing one (ADR-055).
    """

    __tablename__ = "product_overlays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    composition_snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("composition_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    base_image_key = Column(Text, nullable=False)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    versions = relationship(
        "CompositionVersion",
        back_populates="overlay",
        order_by="CompositionVersion.version",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "generation_job_id", name="uq_product_overlays_generation_job_id"
        ),
        Index("idx_product_overlays_created_by", "created_by"),
    )


class CompositionVersion(Base):
    """Append-only rendering of a SKU overlay onto an immutable base image.

    No update or delete path is exposed: a SKU/style change appends a new row
    (ADR-055). `spec_hash` is unique per overlay so identical deterministic
    inputs can never produce a duplicate version (ADR-054); `blocked` versions
    record rejected fit attempts with no rendered output (ADR-056).
    """

    __tablename__ = "composition_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    overlay_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_overlays.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Integer, nullable=False)
    sku_normalized = Column(Text, nullable=False)
    placement = Column(JSONB, nullable=False)
    style = Column(JSONB, nullable=False)
    spec_hash = Column(String(64), nullable=False)
    font_version = Column(String(120), nullable=False)
    status = Column(String(10), nullable=False)
    rendered_key = Column(Text, nullable=True)
    rendered_checksum = Column(String(80), nullable=True)
    fit_result = Column(JSONB, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    overlay = relationship("ProductOverlay", back_populates="versions")

    __table_args__ = (
        UniqueConstraint(
            "overlay_id", "version", name="uq_composition_versions_overlay_version"
        ),
        UniqueConstraint(
            "overlay_id", "spec_hash", name="uq_composition_versions_overlay_spec_hash"
        ),
        CheckConstraint(
            "status IN ('valid', 'blocked')", name="ck_composition_versions_status"
        ),
        Index("idx_composition_versions_overlay_id", "overlay_id"),
    )

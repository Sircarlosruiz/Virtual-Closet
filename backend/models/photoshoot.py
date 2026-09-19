"""Photoshoot aggregate: high-level BFashion request, stages, and result slots."""

import uuid

from sqlalchemy import (
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

PHOTOSHOOT_INPUT_KINDS = ("garment_on_model", "flat_garment")
PHOTOSHOOT_STATUSES = ("queued", "running", "partial", "completed", "failed")
PHOTOSHOOT_STAGE_NAMES = ("tryoff", "vton", "poses", "composition")
PHOTOSHOOT_STAGE_STATUSES = (
    "pending",
    "running",
    "skipped",
    "completed",
    "failed",
)


class Photoshoot(Base):
    """One staff request. expected_results is frozen at submit."""

    __tablename__ = "photoshoots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_link_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_links.id", ondelete="RESTRICT"),
        nullable=False,
    )
    staff_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bridge_source_images.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="RESTRICT"),
        nullable=False,
    )
    input_kind = Column(String(32), nullable=False)
    configuration = Column(JSONB, nullable=False)
    status = Column(String(16), nullable=False, server_default="queued")
    expected_results = Column(Integer, nullable=False)
    idempotency_key = Column(String(255), nullable=True)
    payload_fingerprint = Column(String(64), nullable=True)
    variant_key = Column(String(255), nullable=True)
    error_code = Column(String(80), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    stages = relationship(
        "PhotoshootStage",
        back_populates="photoshoot",
        cascade="all, delete-orphan",
        order_by="PhotoshootStage.name",
    )
    results = relationship(
        "PhotoshootResult",
        back_populates="photoshoot",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "input_kind IN ('garment_on_model', 'flat_garment')",
            name="ck_photoshoots_input_kind",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'partial', 'completed', 'failed')",
            name="ck_photoshoots_status",
        ),
        CheckConstraint("expected_results > 0", name="ck_photoshoots_expected"),
        Index("ix_photoshoots_owned", "tenant_id", "product_link_id", "id"),
        Index("ix_photoshoots_link_status", "product_link_id", "status"),
        Index("ix_photoshoots_source", "source_image_id"),
        Index(
            "uq_photoshoots_link_idempotency",
            "product_link_id",
            "idempotency_key",
            unique=True,
            postgresql_where="idempotency_key IS NOT NULL",
        ),
    )


class PhotoshootStage(Base):
    """One of the four pipeline rows. external_refs holds per-branch jobs."""

    __tablename__ = "photoshoot_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photoshoot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("photoshoots.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, server_default="pending")
    external_job_id = Column(UUID(as_uuid=True), nullable=True)
    external_refs = Column(JSONB, nullable=False, server_default="[]")
    error_code = Column(String(80), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    photoshoot = relationship("Photoshoot", back_populates="stages")

    __table_args__ = (
        UniqueConstraint("photoshoot_id", "name", name="uq_photoshoot_stages_name"),
        CheckConstraint(
            "name IN ('tryoff', 'vton', 'poses', 'composition')",
            name="ck_photoshoot_stages_name",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'skipped', 'completed', 'failed')",
            name="ck_photoshoot_stages_status",
        ),
    )


class PhotoshootResult(Base):
    """One materialized (model, pose) cell bound to a GenerationJob."""

    __tablename__ = "photoshoot_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photoshoot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("photoshoots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    generation_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_id = Column(
        UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pose_id = Column(
        UUID(as_uuid=True),
        ForeignKey("model_photos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    variant_key = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    photoshoot = relationship("Photoshoot", back_populates="results")

    __table_args__ = (
        UniqueConstraint("generation_job_id", name="uq_photoshoot_results_job"),
        UniqueConstraint(
            "photoshoot_id",
            "model_id",
            "pose_id",
            name="uq_photoshoot_results_slot",
        ),
    )

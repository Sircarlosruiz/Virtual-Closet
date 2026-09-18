"""Manual publication selection, per-destination sync, and VC product gallery."""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class PublicationSelection(Base):
    """Staff decision to select or discard one immutable publication candidate.

    Completing a generation job never creates a row here. A new composition
    version is a distinct candidate and requires a new explicit selection
    (ADR-055).
    """

    __tablename__ = "publication_selections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_link_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_links.id", ondelete="CASCADE"),
        nullable=False,
    )
    generation_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    composition_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("composition_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision = Column(Text, nullable=False)
    selected_by = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    deliveries = relationship(
        "SyncDelivery",
        back_populates="selection",
        cascade="all, delete-orphan",
    )
    product_image = relationship(
        "ProductImage",
        back_populates="selection",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "product_link_id",
            "generation_job_id",
            "composition_version_id",
            name="uq_publication_selections_candidate",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "decision IN ('selected', 'discarded')",
            name="ck_publication_selections_decision",
        ),
        Index("idx_publication_selections_link", "product_link_id"),
        Index("idx_publication_selections_job", "generation_job_id"),
        Index("idx_publication_selections_tenant", "tenant_id"),
    )


class SyncDelivery(Base):
    """Idempotent delivery state for one publication destination."""

    __tablename__ = "sync_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_selection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("publication_selections.id", ondelete="CASCADE"),
        nullable=False,
    )
    destination = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="pending")
    retryable = Column(Boolean, nullable=False, server_default="true")
    last_error = Column(Text, nullable=True)
    attempt_count = Column(Integer, nullable=False, server_default="0")
    external_ref = Column(Text, nullable=True)
    durable_object_key = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    selection = relationship("PublicationSelection", back_populates="deliveries")

    __table_args__ = (
        UniqueConstraint(
            "publication_selection_id",
            "destination",
            name="uq_sync_deliveries_selection_destination",
        ),
        CheckConstraint(
            "destination IN ('virtual_closet', 'bfashion')",
            name="ck_sync_deliveries_destination",
        ),
        CheckConstraint(
            "status IN ('pending', 'synced', 'failed')",
            name="ck_sync_deliveries_status",
        ),
        Index("idx_sync_deliveries_selection", "publication_selection_id"),
        Index("idx_sync_deliveries_status", "status"),
    )


class ProductImage(Base):
    """Append-only Virtual Closet gallery image for a linked product.

    Existing rows are never updated or replaced. Retries are deduplicated by
    ``publication_selection_id``.
    """

    __tablename__ = "product_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_link_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_links.id", ondelete="CASCADE"),
        nullable=False,
    )
    prenda_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prenda.id", ondelete="SET NULL"),
        nullable=True,
    )
    publication_selection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("publication_selections.id", ondelete="RESTRICT"),
        nullable=False,
    )
    generation_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    composition_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("composition_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    minio_key = Column(Text, nullable=False)
    configuration = Column(JSONB, nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    selection = relationship("PublicationSelection", back_populates="product_image")

    __table_args__ = (
        UniqueConstraint(
            "publication_selection_id",
            name="uq_product_images_publication_selection",
        ),
        Index("idx_product_images_link", "product_link_id"),
        Index("idx_product_images_tenant", "tenant_id"),
        Index("idx_product_images_link_created", "product_link_id", "created_at"),
    )

import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class CatalogStatus(enum.Enum):
    draft = "draft"
    published = "published"


class Catalogo(Base):
    """A named collection of garment images owned by a mayorista."""

    __tablename__ = "catalogo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    item_count = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    items = relationship(
        "CatalogoItem",
        back_populates="catalogo",
        cascade="all, delete-orphan",
        order_by="CatalogoItem.position",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published')",
            name="ck_catalogo_status",
        ),
        Index("idx_catalogo_mayorista", "mayorista_id"),
        Index("idx_catalogo_mayorista_created", "mayorista_id", "created_at"),
    )


class CatalogoItem(Base):
    """A single garment entry within a catalog."""

    __tablename__ = "catalogo_item"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogo.id", ondelete="CASCADE"),
        nullable=False,
    )
    vton_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vton_jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    garment_name = Column(String(200), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    cloth_type = Column(String(20), nullable=False)
    sku = Column(String(100), nullable=False)
    image_key = Column(String(512), nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    catalogo = relationship("Catalogo", back_populates="items")

    __table_args__ = (
        CheckConstraint(
            "cloth_type IN ('upper_body', 'lower_body', 'dress')",
            name="ck_catalogo_item_cloth_type",
        ),
        UniqueConstraint("catalog_id", "position", name="uq_catalogo_item_position"),
        Index("idx_catalogo_item_catalog", "catalog_id"),
        Index("idx_catalogo_item_catalog_position", "catalog_id", "position"),
    )

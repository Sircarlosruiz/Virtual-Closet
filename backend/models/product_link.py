"""Explicit cross-application product link between an external system and Virtual Closet."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class ProductLink(Base):
    """Authorized mapping from an external product to a Virtual Closet owner.

    Ownership is resolved exclusively through this explicit record; Virtual
    Closet never infers an owner from an external SKU or identifier alone.
    """

    __tablename__ = "product_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system = Column(String(40), nullable=False)
    external_product_id = Column(String(255), nullable=False)
    external_wholesaler_id = Column(String(255), nullable=True)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prenda_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prenda.id", ondelete="SET NULL"),
        nullable=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    mayorista = relationship("Mayorista", foreign_keys=[mayorista_id])
    creator = relationship("Mayorista", foreign_keys=[created_by])
    prenda = relationship("Prenda")
    tenant = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint(
            "system",
            "external_product_id",
            name="uq_product_links_system_external_product",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ProductLink(id={self.id}, system='{self.system}', "
            f"external_product_id='{self.external_product_id}')>"
        )

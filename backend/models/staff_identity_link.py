"""Authorized mapping from an external staff actor to a Virtual Closet mirror."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class StaffIdentityLink(Base):
    """Authorized mapping from an external staff id to a Mayorista mirror.

    Symmetric to ``ProductLink``: uniqueness is ``(system, external_staff_id)``,
    ``system`` and ``tenant_id`` come from the ServiceClient, and revocation is
    logical (``is_active`` / ``revoked_at``). A Mayorista is a bridge mirror
    iff a row in this table points at it (ADR-058).
    """

    __tablename__ = "staff_identity_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system = Column(String(40), nullable=False)
    external_staff_id = Column(String(255), nullable=False)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    mayorista = relationship("Mayorista", foreign_keys=[mayorista_id])
    tenant = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint(
            "system",
            "external_staff_id",
            name="uq_staff_identity_links_system_external_staff",
        ),
        Index(
            "ix_staff_identity_links_tenant_mayorista",
            "tenant_id",
            "mayorista_id",
        ),
        Index("ix_staff_identity_links_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<StaffIdentityLink(id={self.id}, system='{self.system}', "
            f"external_staff_id='{self.external_staff_id}')>"
        )

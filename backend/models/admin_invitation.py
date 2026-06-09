"""Admin invitation model for tenant admin management."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class AdminInvitation(Base):
    """Pending admin invitation to a tenant."""

    __tablename__ = "admin_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    token = Column(String(128), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("mayorista.id"), nullable=False)

    tenant = relationship("Tenant", backref="admin_invitations")
    creator = relationship("Mayorista", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<AdminInvitation(id={self.id}, email='{self.email}', accepted={self.accepted})>"

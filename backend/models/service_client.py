"""Service client model for authenticated server-to-server integration callers."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class ServiceClient(Base):
    """A trusted external service allowed to act on behalf of one tenant.

    The raw secret is never stored; only a bcrypt hash is persisted. Callers
    present ``X-Service-Id`` and ``X-Service-Secret`` headers which are verified
    against ``secret_hash``.
    """

    __tablename__ = "service_clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(80), unique=True, nullable=False)
    system = Column(String(40), nullable=False)
    secret_hash = Column(Text, nullable=False)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, server_default="true")
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tenant = relationship("Tenant")

    __table_args__ = (
        Index("idx_service_clients_system", "system"),
    )

    def __repr__(self) -> str:
        return f"<ServiceClient(id={self.id}, name='{self.name}', system='{self.system}')>"

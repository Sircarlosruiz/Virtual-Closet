"""Buyer link model for audit trail of signed catalog access links."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class BuyerLink(Base):
    """Audit trail for issued signed catalog access links."""

    __tablename__ = "buyer_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    catalog_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)
    token_jti = Column(String(128), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("mayorista.id"), nullable=False)

    tenant = relationship("Tenant", backref="buyer_links")
    creator = relationship("Mayorista", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<BuyerLink(id={self.id}, tenant_id={self.token_jti})>"

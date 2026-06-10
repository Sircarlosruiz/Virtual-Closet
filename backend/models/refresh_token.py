"""Refresh token model for session management."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class RefreshToken(Base):
    """Tracks active refresh tokens for session invalidation."""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(UUID(as_uuid=True), ForeignKey("mayorista.id"), nullable=False, index=True)
    jti = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked = Column(Boolean, nullable=False, server_default="false")

    mayorista = relationship("Mayorista", backref="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, jti='{self.jti[:8]}...', revoked={self.revoked})>"

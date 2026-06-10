"""Unlock token model for account lockout recovery."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class UnlockToken(Base):
    """Single-use token for unlocking a locked account."""

    __tablename__ = "unlock_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("Mayorista", backref="unlock_tokens")

    __table_args__ = (
        Index("idx_unlock_user_unused", "user_id", postgresql_where="used = false"),
    )

    def __repr__(self) -> str:
        return f"<UnlockToken(id={self.id}, user_id={self.user_id}, used={self.used})>"

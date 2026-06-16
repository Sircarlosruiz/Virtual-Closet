"""Password reset token model.

Single-use, time-limited tokens for password recovery.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class PasswordResetToken(Base):
    """Single-use password reset token.

    Tokens are bcrypt-hashed before storage. Each new reset request
    invalidates all previous unused tokens for the user.
    On successful password reset, all active sessions are revoked.
    """

    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(60), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, server_default="false")
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_password_reset_tokens_mayorista_unused", "mayorista_id", "used"),
    )

    mayorista = relationship("Mayorista", backref="password_reset_tokens")

    def __repr__(self) -> str:
        return (
            f"<PasswordResetToken(id={self.id}, mayorista_id={self.mayorista_id}, "
            f"used={self.used}, expires_at={self.expires_at})>"
        )

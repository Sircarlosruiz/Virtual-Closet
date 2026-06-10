"""Email verification token model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class EmailVerificationToken(Base):
    """Single-use token for email verification."""

    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("Mayorista", backref="email_verification_tokens")

    __table_args__ = (
        Index("idx_email_verification_user_unused", "user_id", postgresql_where="used = false"),
    )

    def __repr__(self) -> str:
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id}, used={self.used})>"

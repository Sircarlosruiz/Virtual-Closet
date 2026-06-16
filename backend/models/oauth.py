"""OAuth and SMS OTP models.

Contains OAuthLink for Google identity linking and SmsOtpRecord
for SMS one-time password storage.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class OAuthLink(Base):
    """Links an external OAuth identity to an internal mayorista account.

    Currently supports Google OAuth. The provider_sub field stores the
    Google subject ID, which is stable for a given Google account.
    """

    __tablename__ = "oauth_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(10), nullable=False, server_default="google")
    provider_sub = Column(String(255), nullable=False)
    provider_email = Column(String(255), nullable=False)
    linked_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_sub", name="uq_oauth_link_provider_sub"),
        Index("idx_oauth_links_mayorista", "mayorista_id"),
        Index("idx_oauth_links_provider_sub", "provider", "provider_sub"),
    )

    mayorista = relationship("Mayorista", backref="oauth_links")

    def __repr__(self) -> str:
        return (
            f"<OAuthLink(id={self.id}, provider='{self.provider}', "
            f"provider_sub='{self.provider_sub[:8]}...')>"
        )


class SmsOtpRecord(Base):
    """Active SMS OTP record for a user.

    Only one active OTP per user at a time. The OTP is bcrypt-hashed
    before storage. Sending a new OTP invalidates the previous one.
    Max 3 verification attempts per OTP.
    """

    __tablename__ = "sms_otp_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    otp_hash = Column(String(60), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, server_default="0")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_sms_otp_mayorista", "mayorista_id"),
    )

    mayorista = relationship("Mayorista", backref="sms_otp_record")

    def __repr__(self) -> str:
        return (
            f"<SmsOtpRecord(id={self.id}, mayorista_id={self.mayorista_id}, "
            f"expires_at={self.expires_at}, attempts={self.attempts})>"
        )

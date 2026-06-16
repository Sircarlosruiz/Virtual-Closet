"""Two-factor authentication models.

Contains TwoFactorConfig and BackupCode tables for TOTP and SMS 2FA.
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
    Text,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class TwoFactorConfig(Base):
    """Per-user two-factor authentication configuration.

    Each user has exactly one TwoFactorConfig. The method field determines
    whether TOTP or SMS is the active second factor. Encrypted fields
    (totp_secret_encrypted, phone_number_encrypted) use Fernet symmetric
    encryption (ADR-022).
    """

    __tablename__ = "two_factor_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    method = Column(
        String(4),
        nullable=False,
        server_default="totp",
    )
    totp_secret_encrypted = Column(Text, nullable=True)
    phone_number_encrypted = Column(Text, nullable=True)
    is_configured = Column(Boolean, nullable=False, server_default="false")
    backup_codes_remaining = Column(Integer, nullable=False, server_default="0")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "method IN ('totp', 'sms')",
            name="ck_two_factor_config_method",
        ),
        Index("idx_two_factor_config_mayorista", "mayorista_id"),
    )

    mayorista = relationship("Mayorista", backref="two_factor_config")

    def __repr__(self) -> str:
        return (
            f"<TwoFactorConfig(id={self.id}, mayorista_id={self.mayorista_id}, "
            f"method='{self.method}', is_configured={self.is_configured})>"
        )


class BackupCode(Base):
    """Single-use backup recovery codes for 2FA.

    Eight codes are generated at 2FA setup. Each code is bcrypt-hashed
    before storage. Codes are single-use: once verified, they are marked
    as used and cannot be reused.
    """

    __tablename__ = "backup_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_hash = Column(String(60), nullable=False)
    used = Column(Boolean, nullable=False, server_default="false")
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_backup_codes_mayorista_unused", "mayorista_id", "used"),
    )

    mayorista = relationship("Mayorista", backref="backup_codes")

    def __repr__(self) -> str:
        return (
            f"<BackupCode(id={self.id}, mayorista_id={self.mayorista_id}, "
            f"used={self.used})>"
        )

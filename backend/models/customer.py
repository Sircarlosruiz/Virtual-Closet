import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class Customer(Base):
    """Customer/buyer registered by a mayorista for portal access."""

    __tablename__ = "customer"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="invited")
    invitation_token_hash = Column(String(255), nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    mayorista = relationship("Mayorista", back_populates="customers")

    __table_args__ = (
        UniqueConstraint("mayorista_id", "email", name="uq_customer_mayorista_email"),
        Index("idx_customer_mayorista", "mayorista_id"),
        Index("idx_customer_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, email={self.email}, status={self.status})>"

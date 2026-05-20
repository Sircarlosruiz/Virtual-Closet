import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Mayorista(Base):
    __tablename__ = "mayorista"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    nombre_negocio = Column(String(255), nullable=False)
    plan = Column(String(10), nullable=False, default="base")
    trial_activo = Column(Boolean, nullable=False, default=True)
    trial_expira_en = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + __import__("datetime").timedelta(days=30),
    )
    whatsapp = Column(String(20), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_mayorista_email", "email"),
    )

import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.mayorista import Base


class ModeloIA(Base):
    __tablename__ = "modelo_ia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(UUID(as_uuid=True), ForeignKey("mayorista.id"), nullable=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    thumbnail_key = Column(Text, nullable=False)
    plan_minimo = Column(String(10), nullable=False, default="base")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_modelo_ia_plan_minimo", "plan_minimo"),
        Index("idx_modelo_ia_mayorista", "mayorista_id"),
    )

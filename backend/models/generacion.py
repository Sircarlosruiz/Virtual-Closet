import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.mayorista import Base


class Generacion(Base):
    __tablename__ = "generacion"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(UUID(as_uuid=True), ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False)
    prenda_id = Column(UUID(as_uuid=True), ForeignKey("prenda.id", ondelete="CASCADE"), nullable=False)
    modelo_ia_id = Column(UUID(as_uuid=True), ForeignKey("modelo_ia.id"), nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
    imagen_generada_key = Column(Text, nullable=True)
    thumbnail_key = Column(Text, nullable=True)
    costo_inferencia_usd = Column(Numeric(10, 4), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    prenda = relationship("Prenda")
    modelo_ia = relationship("ModeloIA")

    __table_args__ = (
        Index("idx_generacion_mayorista_id", "mayorista_id"),
        Index("idx_generacion_prenda_id", "prenda_id"),
        Index("idx_generacion_estado", "estado"),
        Index("idx_generacion_prenda_created", "prenda_id", "created_at"),
    )

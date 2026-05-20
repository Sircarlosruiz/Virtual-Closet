import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.mayorista import Base


class Prenda(Base):
    __tablename__ = "prenda"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(UUID(as_uuid=True), ForeignKey("mayorista.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(80), nullable=False)
    imagen_original_url = Column(Text, nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    mayorista = relationship("Mayorista", back_populates="prendas")

    __table_args__ = (
        Index("idx_prenda_mayorista_id", "mayorista_id"),
        Index("idx_prenda_mayorista_created", "mayorista_id", "created_at"),
    )

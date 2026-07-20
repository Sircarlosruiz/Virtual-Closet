import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class Model(Base):
    """A named model identity owned by a mayorista, grouping 1..3 pose photos.

    Pose photos are ModelPhoto rows (models/media.py) linked via model_id.
    Curated and legacy ModelPhoto rows keep model_id = NULL (ADR-012).
    """

    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mayorista_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    mayorista = relationship("Mayorista", back_populates="models")
    pose_photos = relationship("ModelPhoto", back_populates="model")

    __table_args__ = (Index("idx_models_mayorista", "mayorista_id"),)

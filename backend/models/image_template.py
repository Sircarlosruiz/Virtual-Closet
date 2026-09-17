import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.mayorista import Base


class ImageTemplate(Base):
    """Staff-managed, reusable composition configuration."""

    __tablename__ = "image_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(String(10), nullable=False)
    wholesaler_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="CASCADE"),
        nullable=True,
    )
    version = Column(Integer, nullable=False, server_default="1")
    status = Column(String(10), nullable=False, server_default="draft")
    name = Column(String(255), nullable=False)
    model = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    colors = Column(JSONB, nullable=True)
    rack = Column(Text, nullable=True)
    prompt = Column(Text, nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    references = relationship(
        "TemplateReference", back_populates="template", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_image_templates_scope", "scope"),
        Index("idx_image_templates_wholesaler_id", "wholesaler_id"),
        CheckConstraint(
            "scope IN ('common', 'private')", name="ck_image_templates_scope"
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_image_templates_status",
        ),
        CheckConstraint(
            "(scope = 'private' AND wholesaler_id IS NOT NULL) "
            "OR (scope = 'common' AND wholesaler_id IS NULL)",
            name="ck_image_templates_scope_wholesaler",
        ),
    )


class TemplateReference(Base):
    """Optional reference image attached to an `ImageTemplate`."""

    __tablename__ = "template_references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("image_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_key = Column(Text, nullable=False)
    label = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    template = relationship("ImageTemplate", back_populates="references")

    __table_args__ = (Index("idx_template_references_template_id", "template_id"),)

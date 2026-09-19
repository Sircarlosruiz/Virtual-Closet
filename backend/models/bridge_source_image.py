"""Bridge reservation for a staff-browser upload into Virtual Closet storage."""

import uuid

from sqlalchemy import (
    CheckConstraint,
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

SOURCE_IMAGE_KINDS = ("garment_on_model", "flat_garment")
SOURCE_IMAGE_STATUSES = ("pending", "ready", "rejected")
SOURCE_IMAGE_CONTENT_TYPES = ("image/jpeg", "image/png")
REGISTERED_MEDIA_KINDS = ("source_image", "garment_photo")


class BridgeSourceImage(Base):
    """One upload attempt for a ProductLink. Only ``ready`` is usable."""

    __tablename__ = "bridge_source_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_link_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_links.id", ondelete="RESTRICT"),
        nullable=False,
    )
    staff_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mayorista.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind = Column(String(32), nullable=False)
    storage_key = Column(String(512), nullable=False)
    declared_content_type = Column(String(50), nullable=False)
    declared_size_bytes = Column(Integer, nullable=False)
    actual_content_type = Column(String(50), nullable=True)
    actual_size_bytes = Column(Integer, nullable=True)
    status = Column(String(16), nullable=False, server_default="pending")
    rejection_reason = Column(String(255), nullable=True)
    registered_media_id = Column(UUID(as_uuid=True), nullable=True)
    registered_media_kind = Column(String(32), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    product_link = relationship("ProductLink")
    staff = relationship("Mayorista", foreign_keys=[staff_id])
    tenant = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint(
            "storage_key", name="uq_bridge_source_images_storage_key"
        ),
        CheckConstraint(
            "kind IN ('garment_on_model', 'flat_garment')",
            name="ck_bridge_source_images_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'ready', 'rejected')",
            name="ck_bridge_source_images_status",
        ),
        CheckConstraint(
            "declared_content_type IN ('image/jpeg', 'image/png')",
            name="ck_bridge_source_images_declared_type",
        ),
        CheckConstraint(
            "declared_size_bytes > 0",
            name="ck_bridge_source_images_declared_size",
        ),
        Index(
            "ix_bridge_source_images_owned",
            "tenant_id",
            "product_link_id",
            "id",
        ),
        Index(
            "ix_bridge_source_images_link_status",
            "product_link_id",
            "status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<BridgeSourceImage(id={self.id}, status='{self.status}', "
            f"kind='{self.kind}')>"
        )

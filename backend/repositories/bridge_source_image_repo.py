"""Data access for bridge source-image reservations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.bridge_source_image import BridgeSourceImage


class BridgeSourceImageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, row: BridgeSourceImage) -> BridgeSourceImage:
        self._db.add(row)
        await self._db.flush()
        return row

    async def get_owned(
        self, source_image_id: UUID, product_link_id: UUID, tenant_id: UUID
    ) -> BridgeSourceImage | None:
        result = await self._db.execute(
            select(BridgeSourceImage).where(
                BridgeSourceImage.id == source_image_id,
                BridgeSourceImage.product_link_id == product_link_id,
                BridgeSourceImage.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def lock_owned(
        self, source_image_id: UUID, product_link_id: UUID, tenant_id: UUID
    ) -> BridgeSourceImage | None:
        result = await self._db.execute(
            select(BridgeSourceImage)
            .where(
                BridgeSourceImage.id == source_image_id,
                BridgeSourceImage.product_link_id == product_link_id,
                BridgeSourceImage.tenant_id == tenant_id,
            )
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self._db.refresh(row)
        return row

    async def transition_pending_to_ready(
        self,
        source_image_id: UUID,
        *,
        actual_content_type: str,
        actual_size_bytes: int,
        registered_media_id: UUID,
        registered_media_kind: str,
    ) -> bool:
        result = await self._db.execute(
            update(BridgeSourceImage)
            .where(
                BridgeSourceImage.id == source_image_id,
                BridgeSourceImage.status == "pending",
            )
            .values(
                status="ready",
                actual_content_type=actual_content_type,
                actual_size_bytes=actual_size_bytes,
                registered_media_id=registered_media_id,
                registered_media_kind=registered_media_kind,
                confirmed_at=datetime.now(timezone.utc),
            )
        )
        return (result.rowcount or 0) == 1

    async def transition_pending_to_rejected(
        self,
        source_image_id: UUID,
        *,
        reason: str,
        actual_content_type: str | None,
        actual_size_bytes: int | None,
    ) -> bool:
        result = await self._db.execute(
            update(BridgeSourceImage)
            .where(
                BridgeSourceImage.id == source_image_id,
                BridgeSourceImage.status == "pending",
            )
            .values(
                status="rejected",
                rejection_reason=reason,
                actual_content_type=actual_content_type,
                actual_size_bytes=actual_size_bytes,
                confirmed_at=datetime.now(timezone.utc),
            )
        )
        return (result.rowcount or 0) == 1

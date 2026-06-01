import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.media import GarmentPhoto, MediaItem, ModelPhoto


class GarmentPhotoRepo:
    """Data access for GarmentPhoto entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, garment_photo: GarmentPhoto) -> GarmentPhoto:
        self._db.add(garment_photo)
        await self._db.commit()
        await self._db.refresh(garment_photo)
        return garment_photo

    async def get_by_id(
        self, photo_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> GarmentPhoto | None:
        result = await self._db.execute(
            select(GarmentPhoto).where(
                GarmentPhoto.id == photo_id,
                GarmentPhoto.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_mayorista(
        self,
        mayorista_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[GarmentPhoto], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count(GarmentPhoto.id)).where(
            GarmentPhoto.mayorista_id == mayorista_id
        )
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = (
            select(GarmentPhoto)
            .where(GarmentPhoto.mayorista_id == mayorista_id)
            .order_by(GarmentPhoto.uploaded_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(list_stmt)
        items = list(result.scalars().all())
        return items, total


class ModelPhotoRepo:
    """Data access for ModelPhoto entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, model_photo: ModelPhoto) -> ModelPhoto:
        self._db.add(model_photo)
        await self._db.commit()
        await self._db.refresh(model_photo)
        return model_photo

    async def get_by_id(
        self, photo_id: uuid.UUID, mayorista_id: uuid.UUID | None = None
    ) -> ModelPhoto | None:
        stmt = select(ModelPhoto).where(ModelPhoto.id == photo_id)
        if mayorista_id is not None:
            # For own photos, enforce ownership
            stmt = stmt.where(
                ModelPhoto.mayorista_id == mayorista_id,
                ModelPhoto.is_curated.is_(False),
            )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_curated(self) -> list[ModelPhoto]:
        result = await self._db.execute(
            select(ModelPhoto)
            .where(ModelPhoto.is_curated.is_(True))
            .order_by(ModelPhoto.label)
        )
        return list(result.scalars().all())

    async def list_by_mayorista(
        self,
        mayorista_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ModelPhoto], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count(ModelPhoto.id)).where(
            ModelPhoto.mayorista_id == mayorista_id,
            ModelPhoto.is_curated.is_(False),
        )
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = (
            select(ModelPhoto)
            .where(
                ModelPhoto.mayorista_id == mayorista_id,
                ModelPhoto.is_curated.is_(False),
            )
            .order_by(ModelPhoto.uploaded_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(list_stmt)
        items = list(result.scalars().all())
        return items, total


class MediaItemRepo:
    """Data access for MediaItem entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, media_item: MediaItem) -> MediaItem:
        self._db.add(media_item)
        await self._db.commit()
        await self._db.refresh(media_item)
        return media_item

    async def get_by_id(
        self, item_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> MediaItem | None:
        result = await self._db.execute(
            select(MediaItem).where(
                MediaItem.id == item_id,
                MediaItem.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_minio_key(
        self, minio_key: str, mayorista_id: uuid.UUID
    ) -> MediaItem | None:
        result = await self._db.execute(
            select(MediaItem).where(
                MediaItem.minio_key == minio_key,
                MediaItem.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_type(
        self,
        mayorista_id: uuid.UUID,
        media_type: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MediaItem], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count(MediaItem.id)).where(
            MediaItem.mayorista_id == mayorista_id,
            MediaItem.media_type == media_type,
        )
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = (
            select(MediaItem)
            .where(
                MediaItem.mayorista_id == mayorista_id,
                MediaItem.media_type == media_type,
            )
            .order_by(MediaItem.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(list_stmt)
        items = list(result.scalars().all())
        return items, total

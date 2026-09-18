"""Data access for the append-only Virtual Closet product gallery."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.publication import ProductImage


class ProductImageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, image: ProductImage) -> ProductImage:
        self._db.add(image)
        await self._db.flush()
        await self._db.refresh(image)
        return image

    async def get_by_selection(
        self, publication_selection_id: UUID
    ) -> ProductImage | None:
        result = await self._db.execute(
            select(ProductImage).where(
                ProductImage.publication_selection_id == publication_selection_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_link(self, product_link_id: UUID) -> list[ProductImage]:
        result = await self._db.execute(
            select(ProductImage)
            .where(ProductImage.product_link_id == product_link_id)
            .order_by(ProductImage.position, ProductImage.created_at)
        )
        return list(result.scalars().all())

    async def next_position(self, product_link_id: UUID) -> int:
        result = await self._db.execute(
            select(func.coalesce(func.max(ProductImage.position), 0)).where(
                ProductImage.product_link_id == product_link_id
            )
        )
        return int(result.scalar_one()) + 1

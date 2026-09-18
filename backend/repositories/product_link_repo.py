"""Data access for explicit cross-application product links."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.product_link import ProductLink


class ProductLinkRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, link: ProductLink) -> ProductLink:
        self._db.add(link)
        await self._db.commit()
        await self._db.refresh(link)
        return link

    async def get_by_id(self, link_id: UUID) -> ProductLink | None:
        result = await self._db.execute(
            select(ProductLink).where(ProductLink.id == link_id)
        )
        return result.scalar_one_or_none()

    async def get_by_external_product(
        self, system: str, external_product_id: str
    ) -> ProductLink | None:
        """Resolve the explicit link for an external product.

        The external product identifier is only used to *find* the persisted
        link; ownership is always read from the returned record.
        """
        result = await self._db.execute(
            select(ProductLink).where(
                ProductLink.system == system,
                ProductLink.external_product_id == external_product_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: UUID) -> list[ProductLink]:
        result = await self._db.execute(
            select(ProductLink)
            .where(ProductLink.tenant_id == tenant_id)
            .order_by(ProductLink.created_at)
        )
        return list(result.scalars().all())

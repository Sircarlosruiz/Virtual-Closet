import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.catalogo import Catalogo, CatalogoItem


class CatalogoRepo:
    """Data access for Catalogo entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, catalogo: Catalogo) -> Catalogo:
        self._db.add(catalogo)
        await self._db.commit()
        await self._db.refresh(catalogo)
        return catalogo

    async def get_by_id(self, catalog_id: uuid.UUID) -> Catalogo | None:
        result = await self._db.execute(
            select(Catalogo).where(Catalogo.id == catalog_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_mayorista(
        self, catalog_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> Catalogo | None:
        result = await self._db.execute(
            select(Catalogo).where(
                Catalogo.id == catalog_id,
                Catalogo.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def increment_item_count(self, catalog_id: uuid.UUID) -> None:
        await self._db.execute(
            update(Catalogo)
            .where(Catalogo.id == catalog_id)
            .values(item_count=Catalogo.item_count + 1)
        )
        await self._db.commit()

    async def decrement_item_count(self, catalog_id: uuid.UUID) -> None:
        await self._db.execute(
            update(Catalogo)
            .where(Catalogo.id == catalog_id, Catalogo.item_count > 0)
            .values(item_count=Catalogo.item_count - 1)
        )
        await self._db.commit()

    async def update_name(
        self, catalog_id: uuid.UUID, new_name: str
    ) -> Catalogo | None:
        stmt = (
            update(Catalogo)
            .where(Catalogo.id == catalog_id)
            .values(name=new_name, updated_at=func.now())
            .returning(Catalogo)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.scalar_one_or_none()

    async def update_status(
        self, catalog_id: uuid.UUID, new_status: str
    ) -> Catalogo | None:
        stmt = (
            update(Catalogo)
            .where(Catalogo.id == catalog_id)
            .values(status=new_status, updated_at=func.now())
            .returning(Catalogo)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.scalar_one_or_none()

    async def delete(self, catalog_id: uuid.UUID) -> bool:
        stmt = delete(Catalogo).where(Catalogo.id == catalog_id)
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount > 0

    async def list_by_mayorista(
        self, mayorista_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Catalogo], int]:
        offset = (page - 1) * page_size

        count_stmt = select(func.count(Catalogo.id)).where(
            Catalogo.mayorista_id == mayorista_id
        )
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = (
            select(Catalogo)
            .where(Catalogo.mayorista_id == mayorista_id)
            .order_by(Catalogo.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(list_stmt)
        catalogs = list(result.scalars().all())

        return catalogs, total

    async def list_published_by_mayorista(
        self, mayorista_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Catalogo], int]:
        """List published catalogs for a mayorista with pagination."""
        offset = (page - 1) * page_size

        count_stmt = select(func.count(Catalogo.id)).where(
            Catalogo.mayorista_id == mayorista_id,
            Catalogo.status == "published",
        )
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = (
            select(Catalogo)
            .where(
                Catalogo.mayorista_id == mayorista_id,
                Catalogo.status == "published",
            )
            .order_by(Catalogo.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(list_stmt)
        catalogs = list(result.scalars().all())

        return catalogs, total


class CatalogoItemRepo:
    """Data access for CatalogoItem entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, item: CatalogoItem) -> CatalogoItem:
        self._db.add(item)
        await self._db.commit()
        await self._db.refresh(item)
        return item

    async def get_by_id_and_catalog(
        self, item_id: uuid.UUID, catalog_id: uuid.UUID
    ) -> CatalogoItem | None:
        result = await self._db.execute(
            select(CatalogoItem).where(
                CatalogoItem.id == item_id,
                CatalogoItem.catalog_id == catalog_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, item_id: uuid.UUID, catalog_id: uuid.UUID) -> bool:
        item = await self.get_by_id_and_catalog(item_id, catalog_id)
        if item is None:
            return False
        await self._db.delete(item)
        await self._db.commit()
        return True

    async def get_all_by_catalog(self, catalog_id: uuid.UUID) -> list[CatalogoItem]:
        result = await self._db.execute(
            select(CatalogoItem)
            .where(CatalogoItem.catalog_id == catalog_id)
            .order_by(CatalogoItem.position)
        )
        return list(result.scalars().all())

    async def get_max_position(self, catalog_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(func.max(CatalogoItem.position)).where(
                CatalogoItem.catalog_id == catalog_id
            )
        )
        return result.scalar() or 0

    async def update_positions(
        self, item_positions: dict[uuid.UUID, int]
    ) -> None:
        for item_id, position in item_positions.items():
            await self._db.execute(
                update(CatalogoItem)
                .where(CatalogoItem.id == item_id)
                .values(position=position)
            )
        await self._db.commit()

    async def delete_all_by_catalog(self, catalog_id: uuid.UUID) -> int:
        stmt = delete(CatalogoItem).where(
            CatalogoItem.catalog_id == catalog_id
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount

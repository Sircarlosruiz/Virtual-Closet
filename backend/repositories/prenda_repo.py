from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.prenda import Prenda


class PrendaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        mayorista_id: UUID,
        nombre: str,
        imagen_original_url: str,
        *,
        prenda_id: UUID | None = None,
        estado: str = "lista",
    ) -> Prenda:
        prenda = Prenda(
            id=prenda_id or uuid4(),
            mayorista_id=mayorista_id,
            nombre=nombre,
            imagen_original_url=imagen_original_url,
            estado=estado,
        )
        self.session.add(prenda)
        await self.session.commit()
        await self.session.refresh(prenda)
        return prenda

    async def get_by_id(self, prenda_id: UUID, mayorista_id: UUID) -> Prenda | None:
        result = await self.session.execute(
            select(Prenda).where(
                Prenda.id == prenda_id,
                Prenda.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_mayorista(
        self, mayorista_id: UUID, cursor: UUID | None, limit: int = 20
    ) -> list[Prenda]:
        query = (
            select(Prenda)
            .where(Prenda.mayorista_id == mayorista_id)
            .order_by(Prenda.created_at.desc())
            .limit(limit)
        )
        if cursor:
            query = query.where(Prenda.created_at < text(
                f"(SELECT created_at FROM prenda WHERE id = '{cursor}')"
            ))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_this_month(self, mayorista_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Prenda)
            .where(
                Prenda.mayorista_id == mayorista_id,
                Prenda.created_at >= func.date_trunc("month", func.now()),
            )
        )
        return result.scalar_one()

    async def count_by_mayorista(self, mayorista_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Prenda)
            .where(Prenda.mayorista_id == mayorista_id)
        )
        return result.scalar_one()

    async def update_nombre(
        self, prenda_id: UUID, mayorista_id: UUID, nombre: str
    ) -> Prenda:
        prenda = await self.get_by_id(prenda_id, mayorista_id)
        if prenda is None:
            return None
        prenda.nombre = nombre
        await self.session.commit()
        await self.session.refresh(prenda)
        return prenda

    async def delete(self, prenda_id: UUID, mayorista_id: UUID) -> bool:
        prenda = await self.get_by_id(prenda_id, mayorista_id)
        if prenda is None:
            return False
        await self.session.delete(prenda)
        await self.session.commit()
        return True

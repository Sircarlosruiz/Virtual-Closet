from uuid import UUID
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from models.modelo_ia import ModeloIA


class ModeloIARepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> list[ModeloIA]:
        result = await self._db.execute(select(ModeloIA).order_by(ModeloIA.nombre))
        return list(result.scalars().all())

    async def get_by_plan(self, plan: str, mayorista_id: UUID) -> list[ModeloIA]:
        result = await self._db.execute(
            select(ModeloIA)
            .where(
                or_(
                    ModeloIA.mayorista_id.is_(None),
                    ModeloIA.mayorista_id == mayorista_id,
                )
            )
            .order_by(ModeloIA.nombre)
        )
        return list(result.scalars().all())

    async def get_by_id(self, modelo_id: UUID) -> ModeloIA | None:
        result = await self._db.execute(
            select(ModeloIA).where(ModeloIA.id == modelo_id)
        )
        return result.scalar_one_or_none()

    async def create(self, modelo: ModeloIA) -> ModeloIA:
        self._db.add(modelo)
        await self._db.commit()
        await self._db.refresh(modelo)
        return modelo

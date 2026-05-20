from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.modelo_ia import ModeloIA


class ModeloIARepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> list[ModeloIA]:
        result = await self._db.execute(select(ModeloIA).order_by(ModeloIA.nombre))
        return list(result.scalars().all())

    async def get_by_plan(self, plan: str) -> list[ModeloIA]:
        result = await self._db.execute(
            select(ModeloIA)
            .where(ModeloIA.plan_minimo <= plan)
            .order_by(ModeloIA.nombre)
        )
        return list(result.scalars().all())

    async def get_by_id(self, modelo_id: UUID) -> ModeloIA | None:
        result = await self._db.execute(
            select(ModeloIA).where(ModeloIA.id == modelo_id)
        )
        return result.scalar_one_or_none()

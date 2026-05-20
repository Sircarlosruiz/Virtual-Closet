from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models.generacion import Generacion


class GeneracionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, generacion: Generacion) -> Generacion:
        self._db.add(generacion)
        await self._db.commit()
        await self._db.refresh(generacion)
        return generacion

    async def get_by_id(self, generacion_id: UUID) -> Generacion | None:
        result = await self._db.execute(
            select(Generacion).where(Generacion.id == generacion_id)
        )
        return result.scalar_one_or_none()

    async def update_estado(
        self,
        generacion_id: UUID,
        estado: str,
        imagen_generada_key: str | None = None,
        thumbnail_key: str | None = None,
        costo_inferencia_usd: float | None = None,
        error_message: str | None = None,
    ) -> Generacion | None:
        await self._db.execute(
            update(Generacion)
            .where(Generacion.id == generacion_id)
            .values(
                estado=estado,
                imagen_generada_key=imagen_generada_key,
                thumbnail_key=thumbnail_key,
                costo_inferencia_usd=costo_inferencia_usd,
                error_message=error_message,
            )
        )
        await self._db.commit()
        return await self.get_by_id(generacion_id)

    async def list_by_prenda(self, prenda_id: UUID) -> list[Generacion]:
        result = await self._db.execute(
            select(Generacion)
            .where(Generacion.prenda_id == prenda_id)
            .order_by(Generacion.created_at.desc())
        )
        return list(result.scalars().all())

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.model import Model


class ModelRepo:
    """Data access for Model aggregates."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, model: Model) -> Model:
        self._db.add(model)
        await self._db.commit()
        await self._db.refresh(model)
        return model

    async def get_by_id(
        self, model_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> Model | None:
        """Ownership-scoped lookup.

        Returns None when the model does not exist OR belongs to another
        mayorista — both surface as 404 (ADR-013).
        """
        result = await self._db.execute(
            select(Model).where(
                Model.id == model_id,
                Model.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_mayorista(self, mayorista_id: uuid.UUID) -> list[Model]:
        result = await self._db.execute(
            select(Model)
            .where(Model.mayorista_id == mayorista_id)
            .order_by(Model.created_at.desc())
        )
        return list(result.scalars().all())

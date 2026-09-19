"""Persistence for the Photoshoot aggregate."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.photoshoot import Photoshoot, PhotoshootResult, PhotoshootStage


class PhotoshootRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add_aggregate(
        self, photoshoot: Photoshoot, stages: list[PhotoshootStage]
    ) -> Photoshoot:
        self._db.add(photoshoot)
        self._db.add_all(stages)
        await self._db.flush()
        return photoshoot

    async def get(self, photoshoot_id: UUID) -> Photoshoot | None:
        result = await self._db.execute(
            select(Photoshoot)
            .where(Photoshoot.id == photoshoot_id)
            .options(
                selectinload(Photoshoot.stages),
                selectinload(Photoshoot.results),
            )
        )
        return result.scalar_one_or_none()

    async def get_owned(
        self, photoshoot_id: UUID, product_link_id: UUID, tenant_id: UUID
    ) -> Photoshoot | None:
        result = await self._db.execute(
            select(Photoshoot)
            .where(
                Photoshoot.id == photoshoot_id,
                Photoshoot.product_link_id == product_link_id,
                Photoshoot.tenant_id == tenant_id,
            )
            .options(
                selectinload(Photoshoot.stages),
                selectinload(Photoshoot.results),
            )
        )
        return result.scalar_one_or_none()

    async def find_by_idempotency(
        self, product_link_id: UUID, tenant_id: UUID, idempotency_key: str
    ) -> Photoshoot | None:
        result = await self._db.execute(
            select(Photoshoot)
            .where(
                Photoshoot.product_link_id == product_link_id,
                Photoshoot.tenant_id == tenant_id,
                Photoshoot.idempotency_key == idempotency_key,
            )
            .options(
                selectinload(Photoshoot.stages),
                selectinload(Photoshoot.results),
            )
        )
        return result.scalar_one_or_none()

    async def save(self, photoshoot: Photoshoot) -> None:
        photoshoot.updated_at = datetime.now(timezone.utc)
        await self._db.flush()

    async def set_status(
        self, photoshoot_id: UUID, status: str, error_code: str | None = None
    ) -> None:
        values: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if error_code is not None:
            values["error_code"] = error_code
        await self._db.execute(
            update(Photoshoot).where(Photoshoot.id == photoshoot_id).values(**values)
        )

    async def transition_stage(
        self,
        photoshoot_id: UUID,
        name: str,
        *,
        from_statuses: tuple[str, ...],
        to_status: str,
        error_code: str | None = None,
        external_job_id: UUID | None = None,
        external_refs: list | None = None,
        started: bool = False,
        completed: bool = False,
    ) -> bool:
        values: dict = {"status": to_status}
        if error_code is not None:
            values["error_code"] = error_code
        if external_job_id is not None:
            values["external_job_id"] = external_job_id
        if external_refs is not None:
            values["external_refs"] = external_refs
        now = datetime.now(timezone.utc)
        if started:
            values["started_at"] = now
        if completed:
            values["completed_at"] = now
        result = await self._db.execute(
            update(PhotoshootStage)
            .where(
                PhotoshootStage.photoshoot_id == photoshoot_id,
                PhotoshootStage.name == name,
                PhotoshootStage.status.in_(from_statuses),
            )
            .values(**values)
        )
        return result.rowcount == 1

    async def save_external_refs(
        self, photoshoot_id: UUID, name: str, external_refs: list
    ) -> None:
        await self._db.execute(
            update(PhotoshootStage)
            .where(
                PhotoshootStage.photoshoot_id == photoshoot_id,
                PhotoshootStage.name == name,
            )
            .values(external_refs=external_refs)
        )

    async def get_result_by_slot(
        self, photoshoot_id: UUID, model_id: UUID, pose_id: UUID
    ) -> PhotoshootResult | None:
        result = await self._db.execute(
            select(PhotoshootResult).where(
                PhotoshootResult.photoshoot_id == photoshoot_id,
                PhotoshootResult.model_id == model_id,
                PhotoshootResult.pose_id == pose_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_result_if_slot_free(
        self, row: PhotoshootResult
    ) -> PhotoshootResult | None:
        existing = await self.get_result_by_slot(
            row.photoshoot_id, row.model_id, row.pose_id
        )
        if existing is not None:
            return existing
        try:
            async with self._db.begin_nested():
                self._db.add(row)
                await self._db.flush()
        except IntegrityError:
            return await self.get_result_by_slot(
                row.photoshoot_id, row.model_id, row.pose_id
            )
        return row

    async def count_results(self, photoshoot_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count())
            .select_from(PhotoshootResult)
            .where(PhotoshootResult.photoshoot_id == photoshoot_id)
        )
        return int(result.scalar() or 0)

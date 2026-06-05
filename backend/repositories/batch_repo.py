import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.batch_job import BatchItem, BatchJob


class BatchJobRepo:
    """Data access for BatchJob and BatchItem entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_with_items(
        self, batch: BatchJob, items: list[BatchItem]
    ) -> BatchJob:
        """Atomically create a BatchJob with its BatchItem children."""
        self._db.add(batch)
        self._db.add_all(items)
        await self._db.flush()
        return batch

    async def get_by_id_and_mayorista(
        self, batch_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> BatchJob | None:
        """Fetch a batch with its items, scoped to mayorista."""
        stmt = (
            select(BatchJob)
            .where(
                BatchJob.id == batch_id,
                BatchJob.mayorista_id == mayorista_id,
            )
            .options(selectinload(BatchJob.items))
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, batch_id: uuid.UUID) -> BatchJob | None:
        """Fetch a batch without mayorista scoping (internal use)."""
        stmt = (
            select(BatchJob)
            .where(BatchJob.id == batch_id)
            .options(selectinload(BatchJob.items))
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        batch_id: uuid.UUID,
        new_status: str,
        **kwargs,
    ) -> BatchJob | None:
        """Update batch status with optional additional fields."""
        stmt = (
            select(BatchJob)
            .where(BatchJob.id == batch_id)
            .with_for_update()
        )
        result = await self._db.execute(stmt)
        batch = result.scalar_one_or_none()
        if batch is None:
            return None

        batch.status = new_status
        for key, value in kwargs.items():
            setattr(batch, key, value)

        await self._db.flush()
        return batch

    async def update_counters(
        self,
        batch_id: uuid.UUID,
        completed_count: int,
        failed_count: int,
    ) -> BatchJob | None:
        """Update completed and failed item counters."""
        stmt = (
            select(BatchJob)
            .where(BatchJob.id == batch_id)
            .with_for_update()
        )
        result = await self._db.execute(stmt)
        batch = result.scalar_one_or_none()
        if batch is None:
            return None

        batch.completed_count = completed_count
        batch.failed_count = failed_count

        await self._db.flush()
        return batch

    async def save(self, batch: BatchJob) -> None:
        """Persist aggregate changes (flush only, caller commits)."""
        self._db.add(batch)
        await self._db.flush()

    async def list_by_mayorista(
        self,
        mayorista_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BatchJob], int]:
        """Paginated list of mayorista's batches."""
        offset = (page - 1) * page_size
        count_stmt = select(func.count(BatchJob.id)).where(
            BatchJob.mayorista_id == mayorista_id
        )
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = (
            select(BatchJob)
            .where(BatchJob.mayorista_id == mayorista_id)
            .order_by(BatchJob.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(list_stmt)
        items = list(result.scalars().all())
        return items, total

    # --- BatchItem methods ---

    async def get_item_by_id(
        self, item_id: uuid.UUID, batch_id: uuid.UUID
    ) -> BatchItem | None:
        """Fetch a single BatchItem within its batch."""
        stmt = select(BatchItem).where(
            BatchItem.id == item_id,
            BatchItem.batch_id == batch_id,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_item_status(
        self,
        item_id: uuid.UUID,
        new_status: str,
        **kwargs,
    ) -> BatchItem | None:
        """Update a BatchItem's status with optional metadata."""
        stmt = (
            select(BatchItem)
            .where(BatchItem.id == item_id)
            .with_for_update()
        )
        result = await self._db.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            return None

        item.status = new_status
        for key, value in kwargs.items():
            setattr(item, key, value)

        await self._db.flush()
        return item

    async def list_items_by_batch(
        self, batch_id: uuid.UUID
    ) -> list[BatchItem]:
        """All items for a given batch."""
        stmt = (
            select(BatchItem)
            .where(BatchItem.batch_id == batch_id)
            .order_by(BatchItem.created_at)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def set_result_media(
        self, item_id: uuid.UUID, media_id: uuid.UUID
    ) -> None:
        """Set result_media_id on successful media save."""
        stmt = (
            update(BatchItem)
            .where(BatchItem.id == item_id)
            .values(result_media_id=media_id)
        )
        await self._db.execute(stmt)

    async def set_media_save_error(
        self, item_id: uuid.UUID, error_message: str
    ) -> None:
        """Set media_save_error flag on failed media save."""
        stmt = (
            update(BatchItem)
            .where(BatchItem.id == item_id)
            .values(
                media_save_error=True,
                error_message=error_message[:500],
            )
        )
        await self._db.execute(stmt)

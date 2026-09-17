from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.image_template import ImageTemplate


class ImageTemplateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, template: ImageTemplate) -> ImageTemplate:
        self._db.add(template)
        await self._db.commit()
        # Scoped to server-generated columns only — a full refresh() would
        # expire (and force a lazy-load of) the already-populated
        # `references` relationship, which fails outside the session's
        # async-safe read path.
        await self._db.refresh(template, attribute_names=["created_at", "updated_at"])
        return template

    async def save(self, template: ImageTemplate) -> ImageTemplate:
        """Persists changes to an already-tracked template (revision path)."""
        await self._db.commit()
        await self._db.refresh(template, attribute_names=["updated_at"])
        return template

    async def get_by_id(self, template_id: UUID) -> ImageTemplate | None:
        result = await self._db.execute(
            select(ImageTemplate)
            .options(selectinload(ImageTemplate.references))
            .where(ImageTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_for_lock(self, template_id: UUID) -> ImageTemplate | None:
        """Row-level lock for concurrency-safe version bumps."""
        result = await self._db.execute(
            select(ImageTemplate)
            .options(selectinload(ImageTemplate.references))
            .where(ImageTemplate.id == template_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_administrative(
        self,
        scope: str | None = None,
        wholesaler_id: UUID | None = None,
        status: str | None = None,
    ) -> list[ImageTemplate]:
        """Unfiltered listing for staff administration — no scope isolation."""
        stmt = select(ImageTemplate).options(selectinload(ImageTemplate.references))
        if scope is not None:
            stmt = stmt.where(ImageTemplate.scope == scope)
        if wholesaler_id is not None:
            stmt = stmt.where(ImageTemplate.wholesaler_id == wholesaler_id)
        if status is not None:
            stmt = stmt.where(ImageTemplate.status == status)
        result = await self._db.execute(stmt.order_by(ImageTemplate.created_at.desc()))
        return list(result.scalars().all())

    async def list_selectable(self, wholesaler_id: UUID) -> list[ImageTemplate]:
        """Templates a given wholesaler may select: common + their own private, never archived."""
        stmt = (
            select(ImageTemplate)
            .options(selectinload(ImageTemplate.references))
            .where(
                ImageTemplate.status != "archived",
                or_(
                    ImageTemplate.scope == "common",
                    ImageTemplate.wholesaler_id == wholesaler_id,
                ),
            )
            .order_by(ImageTemplate.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def is_selectable_for(
        self, template_id: UUID, wholesaler_id: UUID
    ) -> ImageTemplate | None:
        """Scope-aware read used by the selection path (not administration)."""
        stmt = select(ImageTemplate).where(
            ImageTemplate.id == template_id,
            ImageTemplate.status != "archived",
            or_(
                ImageTemplate.scope == "common",
                ImageTemplate.wholesaler_id == wholesaler_id,
            ),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def archive(self, template_id: UUID) -> ImageTemplate | None:
        await self._db.execute(
            update(ImageTemplate)
            .where(ImageTemplate.id == template_id)
            .values(status="archived")
        )
        await self._db.commit()
        return await self.get_by_id(template_id)

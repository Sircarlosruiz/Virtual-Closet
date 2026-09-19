"""Celery tick for a photoshoot. Only a photoshoot_id crosses the broker (ADR-047, ADR-068)."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import core.database as database
from core.celery_app import app
from core.config import settings
from services.photoshoot_orchestration_service import build_orchestration_service

logger = logging.getLogger(__name__)


async def _tick(photoshoot_id: UUID) -> str:
    async with database.async_session() as db:
        service = build_orchestration_service(db)
        return await service.tick(photoshoot_id)


@app.task(
    bind=True,
    name="tasks.photoshoot_orchestration.photoshoot_tick_task",
    acks_late=True,
    queue="photoshoot",
)
def photoshoot_tick_task(self, photoshoot_id: str) -> None:
    UUID(photoshoot_id)
    outcome = asyncio.run(_tick(UUID(photoshoot_id)))
    if outcome == "reschedule":
        self.apply_async(
            args=[photoshoot_id],
            countdown=settings.PHOTOSHOOT_TICK_COUNTDOWN_SECONDS,
        )

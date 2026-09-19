"""Read-only aggregate photoshoot view for Contract C (FR-8)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.photoshoot import PHOTOSHOOT_STAGE_NAMES, PhotoshootStage
from models.service_client import ServiceClient
from repositories.generation_job_repo import GenerationJobRepository
from repositories.photoshoot_repo import PhotoshootRepository
from repositories.product_link_repo import ProductLinkRepository
from services.photoshoot_errors import (
    PhotoshootNotFoundError,
    PhotoshootProductNotFoundError,
)
from services.photoshoot_status import counters, view_status
from services.product_link_service import ProductLinkError, ProductLinkService
from services.publication_service import (
    PublicationNotFoundError,
    PublicationService,
    preview_object_url,
)

logger = logging.getLogger(__name__)


@dataclass
class PhotoshootResultView:
    generation_job_id: UUID
    model_id: UUID
    pose_id: UUID
    status: str
    preview_url: str | None
    variant_key: str | None


@dataclass
class PhotoshootView:
    photoshoot_id: UUID
    external_product_id: str
    status: str
    variant_key: str | None
    expected_results: int
    completed_results: int
    failed_results: int
    error_code: str | None
    stages: list[PhotoshootStage]
    results: list[PhotoshootResultView]
    candidates: list[dict]


class PhotoshootQueryService:
    def __init__(
        self,
        repo: PhotoshootRepository,
        links: ProductLinkService,
        jobs: GenerationJobRepository,
        publications: PublicationService,
    ) -> None:
        self._repo = repo
        self._links = links
        self._jobs = jobs
        self._publications = publications

    async def get_view(
        self,
        *,
        client: ServiceClient,
        external_product_id: str,
        photoshoot_id: UUID,
        external_wholesaler_id: str | None = None,
    ) -> PhotoshootView:
        try:
            link = await self._links.resolve_active_link(
                client.system,
                external_product_id,
                external_wholesaler_id,
                client.tenant_id,
            )
        except ProductLinkError as exc:
            raise PhotoshootProductNotFoundError("Product link not found") from exc

        photoshoot = await self._repo.get_owned(
            photoshoot_id, link.id, client.tenant_id
        )
        if photoshoot is None:
            raise PhotoshootNotFoundError("Photoshoot not found")

        ordered_stages = _ordered_stages(photoshoot.stages)
        ordered_results = sorted(
            photoshoot.results, key=lambda row: row.created_at
        )
        completed = len(ordered_results)
        status = view_status(
            stages=ordered_stages,
            expected_results=photoshoot.expected_results,
            completed_results=completed,
        )
        tally = counters(
            expected_results=photoshoot.expected_results,
            completed_results=completed,
            stages=ordered_stages,
            configuration=photoshoot.configuration or {},
        )

        result_views: list[PhotoshootResultView] = []
        candidates: list[dict] = []
        for row in ordered_results:
            job = await self._jobs.get_by_id(row.generation_job_id)
            preview = None
            job_status = "completed"
            if job is not None and job.result_key:
                preview = await preview_object_url(job.result_key)
                job_status = job.status
            result_views.append(
                PhotoshootResultView(
                    generation_job_id=row.generation_job_id,
                    model_id=row.model_id,
                    pose_id=row.pose_id,
                    status=job_status,
                    preview_url=preview,
                    variant_key=row.variant_key,
                )
            )
            try:
                candidates.extend(
                    await self._publications.list_candidates(
                        link, row.generation_job_id
                    )
                )
            except PublicationNotFoundError:
                continue

        logger.info(
            "photoshoot_view_read",
            extra={
                "photoshoot_id": str(photoshoot.id),
                "status": status,
                "completed_results": tally.completed_results,
                "failed_results": tally.failed_results,
                "tenant_id": str(client.tenant_id),
            },
        )
        return PhotoshootView(
            photoshoot_id=photoshoot.id,
            external_product_id=external_product_id,
            status=status,
            variant_key=photoshoot.variant_key,
            expected_results=tally.expected_results,
            completed_results=tally.completed_results,
            failed_results=tally.failed_results,
            error_code=photoshoot.error_code,
            stages=ordered_stages,
            results=result_views,
            candidates=candidates,
        )


def _ordered_stages(stages: list[PhotoshootStage]) -> list[PhotoshootStage]:
    rank = {name: index for index, name in enumerate(PHOTOSHOOT_STAGE_NAMES)}
    return sorted(stages, key=lambda stage: rank.get(stage.name, 99))


def build_query_service(db: AsyncSession) -> PhotoshootQueryService:
    from repositories.composition_version_repo import CompositionVersionRepository
    from repositories.product_overlay_repo import ProductOverlayRepository
    from repositories.publication_selection_repo import PublicationSelectionRepository

    jobs = GenerationJobRepository(db)
    return PhotoshootQueryService(
        repo=PhotoshootRepository(db),
        links=ProductLinkService(ProductLinkRepository(db)),
        jobs=jobs,
        publications=PublicationService(
            db,
            PublicationSelectionRepository(db),
            jobs,
            ProductOverlayRepository(db),
            CompositionVersionRepository(db),
            ProductLinkService(ProductLinkRepository(db)),
        ),
    )

"""Orchestrates deterministic SKU composition, versioning, and idempotency."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from api.schemas.composition import CompositionRequest
from models.product_overlay import CompositionVersion, ProductOverlay
from repositories.composition_snapshot_repo import CompositionSnapshotRepository
from repositories.composition_version_repo import (
    CompositionVersionConflictError,
    CompositionVersionRepository,
)
from repositories.generation_job_repo import GenerationJobRepository
from repositories.product_overlay_repo import ProductOverlayRepository
from services import sku_renderer
from services.composition_spec import compute_spec_hash, normalize_sku
from services.storage_service import StorageService

_BASE_BUCKET = "generated"
_OUTPUT_BUCKET = "generated"


class GenerationJobNotFoundError(Exception):
    pass


class CompositionNotFoundError(Exception):
    pass


class BaseImageUnavailableError(Exception):
    """Raised when a job has no durable base image to compose onto."""


class OverlayDoesNotFitError(Exception):
    """Raised when the complete SKU text cannot fit the placement bounds."""

    def __init__(self, message: str, version_id: UUID) -> None:
        super().__init__(message)
        self.version_id = version_id


@dataclass
class ComposeResult:
    overlay: ProductOverlay
    version: CompositionVersion
    created: bool


class SkuCompositionService:
    def __init__(
        self,
        overlays: ProductOverlayRepository,
        versions: CompositionVersionRepository,
        jobs: GenerationJobRepository,
        snapshots: CompositionSnapshotRepository,
        storage: StorageService | None = None,
    ) -> None:
        self._overlays = overlays
        self._versions = versions
        self._jobs = jobs
        self._snapshots = snapshots
        self._storage = storage or StorageService()

    async def compose(
        self, owner_id: UUID, job_id: UUID, request: CompositionRequest
    ) -> ComposeResult:
        job = await self._jobs.get_owned(job_id, owner_id)
        if job is None:
            raise GenerationJobNotFoundError(f"Generation job {job_id} not found")
        if not job.result_key:
            raise BaseImageUnavailableError(
                f"Generation job {job_id} has no completed base image"
            )

        sku = normalize_sku(request.sku)
        font_version = sku_renderer.font_version(request.style.font_family)
        placement = request.placement.model_dump(exclude_none=True)
        style = request.style.model_dump(exclude_none=True)
        spec_hash = compute_spec_hash(
            sku, placement, style, job.result_key, font_version
        )

        overlay = await self._overlays.get_by_generation_job_id(job.id)
        if overlay is None:
            snapshot = await self._snapshots.get_by_generation_job_id(job.id)
            overlay = await self._overlays.create(
                ProductOverlay(
                    generation_job_id=job.id,
                    composition_snapshot_id=snapshot.id if snapshot else None,
                    base_image_key=job.result_key,
                    created_by=owner_id,
                )
            )

        # Row-lock the overlay so version assignment and the spec-hash check
        # serialize (ADR-054/055).
        overlay = await self._overlays.get_by_generation_job_id_for_update(job.id)
        if overlay is None:  # pragma: no cover - defensive, overlay was just ensured
            raise CompositionNotFoundError(
                f"No overlay found for generation job {job_id}"
            )

        existing = await self._versions.find_by_spec_hash(overlay.id, spec_hash)
        if existing is not None:
            return ComposeResult(overlay, existing, created=False)

        if not await self._storage.object_exists(
            job.result_key, bucket_override=_BASE_BUCKET
        ):
            raise BaseImageUnavailableError(
                f"Base image '{job.result_key}' is unavailable in storage"
            )
        base_bytes = await self._storage.get_object_bytes(
            job.result_key, bucket_override=_BASE_BUCKET
        )

        fit = sku_renderer.evaluate_fit(
            sku_renderer.image_size_from_bytes(base_bytes),
            sku,
            request.placement,
            request.style,
        )
        next_version = await self._next_version(overlay.id)

        if not fit["fits"]:
            blocked = await self._versions.append(
                self._build_version(
                    overlay,
                    next_version,
                    sku,
                    placement,
                    style,
                    spec_hash,
                    font_version,
                    status="blocked",
                    rendered_key=None,
                    rendered_checksum=None,
                    fit_result=fit,
                )
            )
            raise OverlayDoesNotFitError(
                fit["reason"] or "SKU does not fit the configured placement",
                blocked.id,
            )

        rendered = sku_renderer.render_composition(
            base_bytes, sku, request.placement, request.style
        )
        rendered_key = f"compositions/{job.id}/{overlay.id}/v{next_version}.png"
        await self._storage.upload_bytes(
            rendered_key,
            rendered,
            content_type="image/png",
            bucket_override=_OUTPUT_BUCKET,
        )
        version = await self._append_with_conflict_recovery(
            self._build_version(
                overlay,
                next_version,
                sku,
                placement,
                style,
                spec_hash,
                font_version,
                status="valid",
                rendered_key=rendered_key,
                rendered_checksum="sha256:" + hashlib.sha256(rendered).hexdigest(),
                fit_result=fit,
            ),
            overlay.id,
            spec_hash,
        )
        return ComposeResult(overlay, version, created=True)

    async def get_summary(
        self, owner_id: UUID, job_id: UUID
    ) -> tuple[ProductOverlay, CompositionVersion | None]:
        await self._require_owned_job(owner_id, job_id)
        overlay = await self._overlays.get_by_generation_job_id(job_id)
        if overlay is None:
            raise CompositionNotFoundError(
                f"No composition found for generation job {job_id}"
            )
        latest = await self._versions.get_latest_by_overlay(overlay.id)
        return overlay, latest

    async def list_versions(
        self, owner_id: UUID, job_id: UUID
    ) -> tuple[ProductOverlay, list[CompositionVersion]]:
        overlay, _ = await self.get_summary(owner_id, job_id)
        versions = await self._versions.list_by_overlay(overlay.id)
        return overlay, versions

    async def get_version(
        self, owner_id: UUID, version_id: UUID
    ) -> tuple[ProductOverlay, CompositionVersion]:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise CompositionNotFoundError(f"Composition version {version_id} not found")
        overlay = await self._overlays.get_by_id(version.overlay_id)
        if overlay is None:
            raise CompositionNotFoundError(f"Composition version {version_id} not found")
        job = await self._jobs.get_owned(overlay.generation_job_id, owner_id)
        if job is None:
            raise CompositionNotFoundError(f"Composition version {version_id} not found")
        return overlay, version

    async def _require_owned_job(self, owner_id: UUID, job_id: UUID):
        job = await self._jobs.get_owned(job_id, owner_id)
        if job is None:
            raise GenerationJobNotFoundError(f"Generation job {job_id} not found")
        return job

    async def _next_version(self, overlay_id: UUID) -> int:
        latest = await self._versions.get_latest_by_overlay(overlay_id)
        return latest.version + 1 if latest else 1

    async def _append_with_conflict_recovery(
        self, version: CompositionVersion, overlay_id: UUID, spec_hash: str
    ) -> CompositionVersion:
        try:
            return await self._versions.append(version)
        except CompositionVersionConflictError:
            existing = await self._versions.find_by_spec_hash(overlay_id, spec_hash)
            if existing is None:
                raise
            return existing

    @staticmethod
    def _build_version(
        overlay: ProductOverlay,
        version_number: int,
        sku: str,
        placement: dict,
        style: dict,
        spec_hash: str,
        font_version: str,
        *,
        status: str,
        rendered_key: str | None,
        rendered_checksum: str | None,
        fit_result: dict,
    ) -> CompositionVersion:
        return CompositionVersion(
            overlay_id=overlay.id,
            version=version_number,
            sku_normalized=sku,
            placement=placement,
            style=style,
            spec_hash=spec_hash,
            font_version=font_version,
            status=status,
            rendered_key=rendered_key,
            rendered_checksum=rendered_checksum,
            fit_result=fit_result,
        )

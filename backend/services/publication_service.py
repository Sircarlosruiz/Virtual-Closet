"""Staff publication decisions: select or discard immutable candidates."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.generation_job import GenerationJob
from models.product_link import ProductLink
from models.product_overlay import CompositionVersion
from models.publication import PublicationSelection
from repositories.composition_version_repo import CompositionVersionRepository
from repositories.generation_job_repo import GenerationJobRepository
from repositories.product_overlay_repo import ProductOverlayRepository
from repositories.publication_selection_repo import PublicationSelectionRepository
from services.product_link_service import ProductLinkService
from services.storage_service import StorageService

_GENERATED_BUCKET = "generated"
_PREVIEW_TTL_SECONDS = 900
DESTINATION_VIRTUAL_CLOSET = "virtual_closet"
DESTINATION_BFASHION = "bfashion"


async def preview_object_url(object_key: str | None) -> str | None:
    """Mint a short-lived preview URL from a durable MinIO key."""
    if not object_key:
        return None
    try:
        return await StorageService().generate_download_url(
            object_key,
            ttl_seconds=_PREVIEW_TTL_SECONDS,
            bucket_override=_GENERATED_BUCKET,
        )
    except Exception:
        return None


class PublicationError(Exception):
    """Base publication domain error."""


class CandidateNotEligibleError(PublicationError):
    """The candidate cannot be selected (incomplete, blocked, or missing bytes)."""


class PublicationNotFoundError(PublicationError):
    """No publication selection exists for this id/scope."""


class DiscardedCannotDeliverError(PublicationError):
    """A discarded candidate cannot be delivered until explicitly selected."""


class PublicationService:
    def __init__(
        self,
        db: AsyncSession,
        selections: PublicationSelectionRepository,
        jobs: GenerationJobRepository,
        overlays: ProductOverlayRepository,
        versions: CompositionVersionRepository,
        product_links: ProductLinkService,
    ) -> None:
        self._db = db
        self._selections = selections
        self._jobs = jobs
        self._overlays = overlays
        self._versions = versions
        self._product_links = product_links

    async def resolve_owned_link(
        self, product_link_id: UUID, tenant_id: UUID
    ) -> ProductLink:
        return await self._product_links.resolve_owned_link(product_link_id, tenant_id)

    async def record_decision(
        self,
        link: ProductLink,
        staff_id: UUID,
        generation_job_id: UUID,
        composition_version_id: UUID | None,
        decision: str,
    ) -> tuple[PublicationSelection, GenerationJob, CompositionVersion | None]:
        job, version, _key = await self._validate_candidate(
            link, generation_job_id, composition_version_id
        )
        existing = await self._selections.get_by_candidate(
            link.id, generation_job_id, composition_version_id
        )
        if existing is None:
            selection = PublicationSelection(
                product_link_id=link.id,
                generation_job_id=generation_job_id,
                composition_version_id=composition_version_id,
                decision=decision,
                selected_by=staff_id,
                mayorista_id=link.mayorista_id,
                tenant_id=link.tenant_id,
            )
            await self._selections.add(selection)
            return selection, job, version

        existing.decision = decision
        existing.selected_by = staff_id
        await self._db.flush()
        await self._db.refresh(existing)
        return existing, job, version

    async def load_candidate(
        self,
        link: ProductLink,
        generation_job_id: UUID,
        composition_version_id: UUID | None,
    ) -> tuple[GenerationJob, CompositionVersion | None, str]:
        return await self._validate_candidate(
            link, generation_job_id, composition_version_id
        )

    async def get_owned_selection(
        self, selection_id: UUID, link: ProductLink
    ) -> PublicationSelection:
        selection = await self._selections.get_by_id(selection_id)
        if selection is None or selection.product_link_id != link.id:
            raise PublicationNotFoundError("Publication not found")
        return selection

    async def list_candidates(
        self, link: ProductLink, generation_job_id: UUID
    ) -> list[dict]:
        job = await self._jobs.get_owned(generation_job_id, link.mayorista_id)
        if job is None:
            raise PublicationNotFoundError("Generation job not found")

        decisions = {
            (row.composition_version_id, row.decision, row.id)
            for row in await self._selections.list_by_job_and_link(link.id, job.id)
        }
        decision_by_version = {
            version_id: (decision, selection_id)
            for version_id, decision, selection_id in decisions
        }

        candidates: list[dict] = []
        if job.status == "completed" and job.result_key:
            decision, selection_id = decision_by_version.get(None, (None, None))
            candidates.append(
                await self._candidate_payload(
                    job,
                    version=None,
                    decision=decision,
                    publication_id=selection_id,
                )
            )

        overlay = await self._overlays.get_by_generation_job_id(job.id)
        if overlay is None:
            return candidates

        for version in await self._versions.list_by_overlay(overlay.id):
            if version.status != "valid" or not version.rendered_key:
                continue
            decision, selection_id = decision_by_version.get(version.id, (None, None))
            candidates.append(
                await self._candidate_payload(
                    job,
                    version=version,
                    decision=decision,
                    publication_id=selection_id,
                )
            )
        return candidates

    async def preview_url(self, object_key: str | None) -> str | None:
        return await preview_object_url(object_key)

    async def _validate_candidate(
        self,
        link: ProductLink,
        generation_job_id: UUID,
        composition_version_id: UUID | None,
    ) -> tuple[GenerationJob, CompositionVersion | None, str]:
        job = await self._jobs.get_owned(generation_job_id, link.mayorista_id)
        if job is None:
            raise PublicationNotFoundError("Generation job not found")
        if job.status != "completed" or not job.result_key:
            raise CandidateNotEligibleError(
                "Generation result is not complete and cannot be published"
            )

        if composition_version_id is None:
            return job, None, job.result_key

        version = await self._versions.get_by_id(composition_version_id)
        overlay = None
        if version is not None:
            overlay = await self._overlays.get_by_id(version.overlay_id)
        if version is None or overlay is None or overlay.generation_job_id != job.id:
            raise PublicationNotFoundError("Composition version not found")
        if version.status != "valid" or not version.rendered_key:
            raise CandidateNotEligibleError(
                "Composition version is not eligible for publication"
            )
        return job, version, version.rendered_key

    async def _candidate_payload(
        self,
        job: GenerationJob,
        version: CompositionVersion | None,
        decision: str | None,
        publication_id,
    ) -> dict:
        key = version.rendered_key if version is not None else job.result_key
        return {
            "generation_job_id": job.id,
            "composition_version_id": version.id if version is not None else None,
            "kind": (
                "composition_version" if version is not None else "generation_result"
            ),
            "durable_object_key": key,
            "preview_url": await self.preview_url(key),
            "decision": decision,
            "publication_id": publication_id,
            "eligible": True,
        }

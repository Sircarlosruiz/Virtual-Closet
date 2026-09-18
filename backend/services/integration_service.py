"""Orchestration for the authenticated cross-application generation bridge.

Virtual Closet remains the single generation authority: the bridge resolves an
explicit product link, validates the asserted staff actor against Virtual
Closet's own records, and then delegates to the existing generation pipeline.
"""

from uuid import UUID

from api.schemas.image_generation import ImageGenerationRequest
from models.generation_job import GenerationJob
from models.product_link import ProductLink
from models.service_client import ServiceClient
from repositories.generation_job_repo import GenerationJobRepository
from repositories.mayorista_repo import MayoristaRepository
from services.image_generation_service import ImageGenerationService
from services.product_link_service import ProductLinkService

STAFF_ROLES = {"admin", "owner", "staff"}


class StaffNotAuthorizedError(Exception):
    """The asserted staff actor is unknown, not staff, or cross-tenant."""


class BridgeGenerationJobNotFoundError(Exception):
    """The generation job is not owned by the linked Virtual Closet entity."""


class IntegrationService:
    def __init__(
        self,
        product_links: ProductLinkService,
        mayoristas: MayoristaRepository,
        image_generation: ImageGenerationService,
        jobs: GenerationJobRepository,
    ) -> None:
        self._product_links = product_links
        self._mayoristas = mayoristas
        self._image_generation = image_generation
        self._jobs = jobs

    async def create_product_generation(
        self,
        service_client: ServiceClient,
        staff_id: UUID,
        external_product_id: str,
        external_wholesaler_id: str | None,
        generation: ImageGenerationRequest,
        idempotency_key: str | None = None,
    ) -> tuple[GenerationJob, bool, ProductLink]:
        link = await self._product_links.resolve_active_link(
            system=service_client.system,
            external_product_id=external_product_id,
            external_wholesaler_id=external_wholesaler_id,
            tenant_id=service_client.tenant_id,
        )
        await self._authorize_staff(staff_id, link)

        job, created = await self._image_generation.create_job(
            link.mayorista_id, generation, idempotency_key
        )
        return job, created, link

    async def get_product_generation(
        self,
        service_client: ServiceClient,
        external_product_id: str,
        external_wholesaler_id: str | None,
        job_id: UUID,
    ) -> tuple[GenerationJob, ProductLink]:
        link = await self._product_links.resolve_active_link(
            system=service_client.system,
            external_product_id=external_product_id,
            external_wholesaler_id=external_wholesaler_id,
            tenant_id=service_client.tenant_id,
        )
        job = await self._jobs.get_owned(job_id, link.mayorista_id)
        if job is None:
            raise BridgeGenerationJobNotFoundError("Generation job not found")
        return job, link

    async def _authorize_staff(self, staff_id: UUID, link: ProductLink) -> None:
        staff = await self._mayoristas.get_by_id(staff_id)
        if staff is None or staff.role not in STAFF_ROLES:
            raise StaffNotAuthorizedError("Staff access required")
        if staff.tenant_id is None or staff.tenant_id != link.tenant_id:
            raise StaffNotAuthorizedError("Staff actor does not belong to this tenant")

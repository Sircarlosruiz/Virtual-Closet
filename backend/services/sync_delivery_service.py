"""Idempotent per-destination delivery of selected publication candidates."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.composition_snapshot import CompositionSnapshot
from models.generation_job import GenerationJob
from models.product_link import ProductLink
from models.product_overlay import CompositionVersion
from models.publication import ProductImage, PublicationSelection, SyncDelivery
from repositories.composition_snapshot_repo import CompositionSnapshotRepository
from repositories.product_image_repo import ProductImageRepository
from repositories.sync_delivery_repo import SyncDeliveryRepository
from services.bfashion_sync_adapter import (
    BFashionImageIngest,
    BFashionSyncAdapter,
    BFashionSyncError,
)
from services.publication_service import (
    DESTINATION_BFASHION,
    DESTINATION_VIRTUAL_CLOSET,
    DiscardedCannotDeliverError,
)

_CONTENT_TYPE = "image/png"


class SyncDeliveryService:
    def __init__(
        self,
        db: AsyncSession,
        deliveries: SyncDeliveryRepository,
        images: ProductImageRepository,
        snapshots: CompositionSnapshotRepository,
        bfashion: BFashionSyncAdapter,
    ) -> None:
        self._db = db
        self._deliveries = deliveries
        self._images = images
        self._snapshots = snapshots
        self._bfashion = bfashion

    async def sync_selection(
        self,
        selection: PublicationSelection,
        link: ProductLink,
        job: GenerationJob,
        version: CompositionVersion | None,
        *,
        retry_only_failed: bool = False,
    ) -> list[SyncDelivery]:
        if selection.decision != "selected":
            raise DiscardedCannotDeliverError(
                "Discarded results cannot be delivered until explicitly selected"
            )

        durable_key = version.rendered_key if version is not None else job.result_key
        configuration = await self._configuration_copy(job, version)
        await self._ensure_pending_rows(selection, durable_key)
        await self._deliver_virtual_closet(
            selection, link, job, version, durable_key, configuration
        )
        await self._db.commit()

        bfashion = await self._deliveries.get_by_selection_and_destination(
            selection.id, DESTINATION_BFASHION
        )
        if bfashion is not None and self._should_attempt(bfashion, retry_only_failed):
            await self._deliver_bfashion(
                bfashion, selection, link, job, version, durable_key, configuration
            )
            await self._db.commit()

        return await self._deliveries.list_by_selection(selection.id)

    async def list_deliveries(self, selection_id: UUID) -> list[SyncDelivery]:
        return await self._deliveries.list_by_selection(selection_id)

    async def _ensure_pending_rows(
        self, selection: PublicationSelection, durable_key: str | None
    ) -> None:
        for destination in (DESTINATION_VIRTUAL_CLOSET, DESTINATION_BFASHION):
            existing = await self._deliveries.get_by_selection_and_destination(
                selection.id, destination
            )
            if existing is None:
                await self._deliveries.add(
                    SyncDelivery(
                        publication_selection_id=selection.id,
                        destination=destination,
                        status="pending",
                        retryable=True,
                        durable_object_key=durable_key,
                    )
                )
            elif existing.durable_object_key is None and durable_key:
                existing.durable_object_key = durable_key

    async def _deliver_virtual_closet(
        self,
        selection: PublicationSelection,
        link: ProductLink,
        job: GenerationJob,
        version: CompositionVersion | None,
        durable_key: str | None,
        configuration: dict,
    ) -> None:
        delivery = await self._deliveries.get_by_selection_and_destination(
            selection.id, DESTINATION_VIRTUAL_CLOSET
        )
        if delivery is None or delivery.status == "synced":
            return
        if not durable_key:
            delivery.status = "failed"
            delivery.retryable = False
            delivery.last_error = "Missing durable object key"
            delivery.attempt_count += 1
            return

        existing = await self._images.get_by_selection(selection.id)
        if existing is None:
            image = ProductImage(
                product_link_id=link.id,
                prenda_id=link.prenda_id,
                publication_selection_id=selection.id,
                generation_job_id=job.id,
                composition_version_id=version.id if version is not None else None,
                mayorista_id=link.mayorista_id,
                tenant_id=link.tenant_id,
                minio_key=durable_key,
                configuration=configuration,
                position=await self._images.next_position(link.id),
            )
            existing = await self._images.add(image)

        delivery.status = "synced"
        delivery.retryable = False
        delivery.last_error = None
        delivery.attempt_count += 1
        delivery.durable_object_key = durable_key
        delivery.external_ref = str(existing.id)

    async def _deliver_bfashion(
        self,
        delivery: SyncDelivery,
        selection: PublicationSelection,
        link: ProductLink,
        job: GenerationJob,
        version: CompositionVersion | None,
        durable_key: str | None,
        configuration: dict,
    ) -> None:
        if not durable_key:
            delivery.status = "failed"
            delivery.retryable = False
            delivery.last_error = "Missing durable object key"
            delivery.attempt_count += 1
            return

        delivery.attempt_count += 1
        delivery.durable_object_key = durable_key
        try:
            result = await self._bfashion.upsert_product_image(
                BFashionImageIngest(
                    external_product_id=link.external_product_id,
                    publication_selection_id=selection.id,
                    generation_job_id=job.id,
                    composition_version_id=(
                        version.id if version is not None else None
                    ),
                    durable_object_key=durable_key,
                    content_type=_CONTENT_TYPE,
                    configuration=configuration,
                    staff_id=selection.selected_by,
                )
            )
        except BFashionSyncError as exc:
            delivery.status = "failed"
            delivery.retryable = exc.retryable
            delivery.last_error = str(exc)
            return

        delivery.status = "synced"
        delivery.retryable = False
        delivery.last_error = None
        delivery.external_ref = result.external_ref

    async def _configuration_copy(
        self, job: GenerationJob, version: CompositionVersion | None
    ) -> dict:
        snapshot: (
            CompositionSnapshot | None
        ) = await self._snapshots.get_by_generation_job_id(job.id)
        return {
            "generation_job_id": str(job.id),
            "mode": job.mode,
            "provider": job.provider,
            "composition_version_id": str(version.id) if version is not None else None,
            "composition_version": version.version if version is not None else None,
            "sku_normalized": (version.sku_normalized if version is not None else None),
            "template_id": str(snapshot.template_id) if snapshot else None,
            "template_version": snapshot.template_version if snapshot else None,
            "snapshot": snapshot.effective_configuration if snapshot else None,
        }

    @staticmethod
    def _should_attempt(delivery: SyncDelivery, _retry_only_failed: bool) -> bool:
        if delivery.status == "synced":
            return False
        if delivery.status == "pending":
            return True
        return delivery.retryable

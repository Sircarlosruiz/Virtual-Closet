"""Advance a photoshoot one tick (ADR-067, ADR-068)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from api.schemas.composition import CompositionRequest, OverlayPlacement, OverlayStyle
from core.config import settings
from core.minio_client import MinIOClient
from models.photoshoot import Photoshoot, PhotoshootStage
from repositories.batch_repo import BatchJobRepo
from repositories.composition_snapshot_repo import CompositionSnapshotRepository
from repositories.composition_version_repo import CompositionVersionRepository
from repositories.generation_job_repo import GenerationJobRepository
from repositories.media_repo import GarmentPhotoRepo, MediaItemRepo, ModelPhotoRepo
from repositories.model_repo import ModelRepo
from repositories.photoshoot_repo import PhotoshootRepository
from repositories.pose_set_repo import PoseSetRepo
from repositories.product_overlay_repo import ProductOverlayRepository
from repositories.tryoff_job_repo import SourceImageRepo, TryoffJobRepo
from repositories.vton_job_repo import VTONJobRepo
from services.batch_submission_service import BatchSubmissionService
from services.media_service import MediaUploadService
from services.photoshoot_materialization_service import PhotoshootMaterializationService
from services.photoshoot_status import derive
from services.pose_set_service import (
    DuplicatePoseSelectionError,
    EmptyPoseSelectionError,
    InvalidPoseSelectionError,
    PoseSetSubmissionService,
)
from services.sku_composition_service import (
    OverlayDoesNotFitError,
    SkuCompositionService,
)
from services.storage_service import StorageService
from services.tryoff_job_service import (
    SourceImageNotFoundError,
    SourceImageOwnershipError,
    TryoffJobService,
)
from services.vton_job_service import (
    PhotoNotFoundError,
    PhotoOwnershipError,
    VTONJobService,
)

logger = logging.getLogger(__name__)

CLOTH_TO_TRYOFF = {
    "upper_body": "upper",
    "lower_body": "lower",
    "dress": "dress",
}

TickOutcome = str  # "done" | "reschedule"


class PhotoshootOrchestrationService:
    def __init__(
        self,
        db: AsyncSession,
        repo: PhotoshootRepository,
        tryoff: TryoffJobService,
        tryoff_jobs: TryoffJobRepo,
        vton: VTONJobService,
        poses: PoseSetSubmissionService,
        batches: BatchJobRepo,
        batch_submit: BatchSubmissionService,
        media: MediaItemRepo,
        garments: GarmentPhotoRepo,
        garment_upload: MediaUploadService,
        materializer: PhotoshootMaterializationService,
        composition: SkuCompositionService,
        overlays: ProductOverlayRepository,
        storage: StorageService,
    ) -> None:
        self._db = db
        self._repo = repo
        self._tryoff = tryoff
        self._tryoff_jobs = tryoff_jobs
        self._vton = vton
        self._poses = poses
        self._batches = batches
        self._batch_submit = batch_submit
        self._media = media
        self._garments = garments
        self._garment_upload = garment_upload
        self._materializer = materializer
        self._composition = composition
        self._overlays = overlays
        self._storage = storage
        self._pending_tryoff_ids: list[UUID] = []

    def publish_pending(self) -> None:
        self._batch_submit.publish_pending()
        pending = self._pending_tryoff_ids
        self._pending_tryoff_ids = []
        publish = getattr(self._tryoff, "publish_job", TryoffJobService.publish_job)
        for job_id in pending:
            publish(job_id)

    async def tick(self, photoshoot_id: UUID) -> TickOutcome:
        photoshoot = await self._repo.get(photoshoot_id)
        if photoshoot is None:
            return "done"
        if photoshoot.status in {"completed", "partial", "failed"}:
            return "done"

        config = dict(photoshoot.configuration or {})
        ticks = int(config.get("tick_count") or 0) + 1
        config["tick_count"] = ticks
        if ticks > settings.PHOTOSHOOT_MAX_TICKS:
            photoshoot.error_code = "PHOTOSHOOT_TICK_LIMIT"
            self._write_config(photoshoot, config)
            await self._finalize(photoshoot, work_pending=False)
            await self._db.commit()
            return "done"

        if photoshoot.status == "queued":
            photoshoot.status = "running"

        stages = {stage.name: stage for stage in photoshoot.stages}
        await self._advance_tryoff(photoshoot, stages.get("tryoff"), config)
        await self._advance_vton(photoshoot, stages.get("vton"), config)
        await self._advance_poses(photoshoot, stages.get("poses"), config)
        await self._materialize_ready(photoshoot, stages.get("poses"), config)
        await self._advance_composition(photoshoot, stages.get("composition"), config)

        self._write_config(photoshoot, config)
        work_pending = self._has_work(stages)
        await self._finalize(photoshoot, work_pending=work_pending)
        await self._db.commit()
        self.publish_pending()
        return "reschedule" if photoshoot.status == "running" else "done"

    @staticmethod
    def _write_config(photoshoot: Photoshoot, config: dict) -> None:
        photoshoot.configuration = config
        flag_modified(photoshoot, "configuration")

    def _has_work(self, stages: dict[str, PhotoshootStage]) -> bool:
        return any(
            stage.status in {"pending", "running"}
            for name in ("tryoff", "vton", "poses", "composition")
            if (stage := stages.get(name)) is not None
        )

    async def _finalize(self, photoshoot: Photoshoot, *, work_pending: bool) -> None:
        completed = await self._repo.count_results(photoshoot.id)
        photoshoot.status = derive(
            expected_results=photoshoot.expected_results,
            completed_results=completed,
            work_pending=work_pending,
        )
        await self._repo.save(photoshoot)

    async def _advance_tryoff(
        self, photoshoot: Photoshoot, stage: PhotoshootStage | None, config: dict
    ) -> None:
        if stage is None or stage.status in {"skipped", "completed", "failed"}:
            return
        if photoshoot.input_kind == "flat_garment":
            return
        if stage.status == "pending":
            source_raw = config.get("registered_media_id")
            if not source_raw:
                stage.status = "failed"
                stage.error_code = "TRYOFF_FAILED"
                stage.completed_at = datetime.now(timezone.utc)
                photoshoot.error_code = "TRYOFF_FAILED"
                return
            garment_type = CLOTH_TO_TRYOFF.get(config["cloth_type"], "upper")
            try:
                job = await self._tryoff.submit_job(
                    photoshoot.mayorista_id,
                    UUID(source_raw),
                    garment_type,
                    commit=False,
                    publish=False,
                )
            except (SourceImageNotFoundError, SourceImageOwnershipError):
                stage.status = "failed"
                stage.error_code = "TRYOFF_FAILED"
                stage.completed_at = datetime.now(timezone.utc)
                photoshoot.error_code = "TRYOFF_FAILED"
                logger.warning(
                    "stage_failed",
                    extra={
                        "photoshoot_id": str(photoshoot.id),
                        "stage": "tryoff",
                        "error_code": "TRYOFF_FAILED",
                    },
                )
                return
            stage.status = "running"
            stage.started_at = datetime.now(timezone.utc)
            stage.external_job_id = job.id
            self._pending_tryoff_ids.append(job.id)
            logger.info(
                "stage_started",
                extra={"photoshoot_id": str(photoshoot.id), "stage": "tryoff"},
            )
            return
        if stage.external_job_id is None:
            return
        job = await self._tryoff_jobs.get_by_id(stage.external_job_id)
        if job is None:
            return
        if job.status == "complete" and job.output_minio_key:
            garment_id = await self._ensure_extracted_garment(
                photoshoot, job.output_minio_key
            )
            config["garment_id_effective"] = str(garment_id)
            stage.status = "completed"
            stage.completed_at = datetime.now(timezone.utc)
            logger.info(
                "stage_completed",
                extra={"photoshoot_id": str(photoshoot.id), "stage": "tryoff"},
            )
            return
        if job.status == "failed":
            stage.status = "failed"
            stage.error_code = "TRYOFF_FAILED"
            stage.completed_at = datetime.now(timezone.utc)
            photoshoot.error_code = "TRYOFF_FAILED"
            logger.warning(
                "stage_failed",
                extra={
                    "photoshoot_id": str(photoshoot.id),
                    "stage": "tryoff",
                    "error_code": "TRYOFF_FAILED",
                },
            )

    async def _ensure_extracted_garment(
        self, photoshoot: Photoshoot, source_key: str
    ) -> UUID:
        dest_key = f"garments/{photoshoot.mayorista_id}/photoshoots/{photoshoot.id}.png"
        existing = await self._garments.get_by_minio_key(
            dest_key, photoshoot.mayorista_id
        )
        if existing is not None:
            return existing.id
        data = await self._storage.get_object_bytes(
            source_key, bucket_override="generated"
        )
        if not await self._storage.object_exists(dest_key, bucket_override="originals"):
            await self._storage.upload_bytes(
                dest_key,
                data,
                content_type="image/png",
                bucket_override="originals",
            )
        garment = await self._garment_upload.register_existing_garment(
            photoshoot.mayorista_id,
            photoshoot.tenant_id,
            dest_key,
            f"{photoshoot.id}.png",
            "image/png",
            len(data),
        )
        return garment.id

    async def _advance_vton(
        self, photoshoot: Photoshoot, stage: PhotoshootStage | None, config: dict
    ) -> None:
        if stage is None or stage.status in {"skipped", "completed", "failed"}:
            return
        tryoff = next(s for s in photoshoot.stages if s.name == "tryoff")
        if tryoff.status == "failed":
            stage.status = "failed"
            stage.error_code = "TRYOFF_FAILED"
            stage.completed_at = datetime.now(timezone.utc)
            return
        if tryoff.status not in {"completed", "skipped"}:
            return
        garment_id = config.get("garment_id_effective")
        if not garment_id:
            stage.status = "failed"
            stage.error_code = "VTON_GATE_FAILED"
            stage.completed_at = datetime.now(timezone.utc)
            photoshoot.error_code = "VTON_GATE_FAILED"
            return
        refs = list(stage.external_refs or [])
        known = {ref.get("model_id") for ref in refs}
        if stage.status == "pending":
            stage.status = "running"
            stage.started_at = datetime.now(timezone.utc)
            logger.info(
                "stage_started",
                extra={"photoshoot_id": str(photoshoot.id), "stage": "vton"},
            )
        for model_id, poses in (config.get("resolved_poses") or {}).items():
            if model_id in known:
                continue
            photo_id = UUID(poses[0]["model_photo_id"])
            try:
                await self._vton.validate_pairing(
                    photoshoot.mayorista_id,
                    UUID(garment_id),
                    photo_id,
                    config.get("cloth_type"),
                )
                refs.append(
                    {
                        "model_id": model_id,
                        "kind": "vton_validate",
                        "id": None,
                        "status": "completed",
                        "error_code": None,
                    }
                )
            except (PhotoNotFoundError, PhotoOwnershipError):
                refs.append(
                    {
                        "model_id": model_id,
                        "kind": "vton_validate",
                        "id": None,
                        "status": "failed",
                        "error_code": "VTON_GATE_FAILED",
                    }
                )
                logger.warning(
                    "branch_failed",
                    extra={
                        "photoshoot_id": str(photoshoot.id),
                        "model_id": model_id,
                        "error_code": "VTON_GATE_FAILED",
                    },
                )
        stage.external_refs = refs
        flag_modified(stage, "external_refs")
        living = [ref for ref in refs if ref.get("status") == "completed"]
        failed = [ref for ref in refs if ref.get("status") == "failed"]
        expected = len(config.get("resolved_poses") or {})
        if len(refs) < expected:
            return
        if living:
            stage.status = "completed"
            stage.completed_at = datetime.now(timezone.utc)
            logger.info(
                "stage_completed",
                extra={"photoshoot_id": str(photoshoot.id), "stage": "vton"},
            )
        elif failed:
            stage.status = "failed"
            stage.error_code = "VTON_GATE_FAILED"
            stage.completed_at = datetime.now(timezone.utc)
            photoshoot.error_code = "VTON_GATE_FAILED"
            logger.warning(
                "stage_failed",
                extra={
                    "photoshoot_id": str(photoshoot.id),
                    "stage": "vton",
                    "error_code": "VTON_GATE_FAILED",
                },
            )

    def _living_model_ids(self, photoshoot: Photoshoot) -> list[str]:
        vton = next(s for s in photoshoot.stages if s.name == "vton")
        return [
            ref["model_id"]
            for ref in (vton.external_refs or [])
            if ref.get("status") == "completed"
        ]

    async def _advance_poses(
        self, photoshoot: Photoshoot, stage: PhotoshootStage | None, config: dict
    ) -> None:
        if stage is None or stage.status in {"skipped", "completed", "failed"}:
            return
        vton = next(s for s in photoshoot.stages if s.name == "vton")
        if vton.status == "failed":
            stage.status = "failed"
            stage.error_code = "VTON_GATE_FAILED"
            stage.completed_at = datetime.now(timezone.utc)
            return
        if vton.status != "completed":
            return
        garment_id = config.get("garment_id_effective")
        if not garment_id:
            return
        if stage.status == "pending":
            stage.status = "running"
            stage.started_at = datetime.now(timezone.utc)
            logger.info(
                "stage_started",
                extra={"photoshoot_id": str(photoshoot.id), "stage": "poses"},
            )
        refs = list(stage.external_refs or [])
        known = {ref.get("model_id") for ref in refs}
        for model_id in self._living_model_ids(photoshoot):
            if model_id in known:
                continue
            pose_ids = [
                UUID(item["model_photo_id"])
                for item in config["resolved_poses"][model_id]
            ]
            try:
                pose_set, batch = await self._poses.submit(
                    photoshoot.mayorista_id,
                    photoshoot.tenant_id,
                    UUID(garment_id),
                    UUID(model_id),
                    config["cloth_type"],
                    pose_ids,
                )
            except (
                EmptyPoseSelectionError,
                DuplicatePoseSelectionError,
                InvalidPoseSelectionError,
            ):
                refs.append(
                    {
                        "model_id": model_id,
                        "kind": "pose_set",
                        "id": None,
                        "status": "failed",
                        "error_code": "POSE_SET_FAILED",
                    }
                )
                logger.warning(
                    "branch_failed",
                    extra={
                        "photoshoot_id": str(photoshoot.id),
                        "model_id": model_id,
                        "error_code": "POSE_SET_FAILED",
                    },
                )
                continue
            refs.append(
                {
                    "model_id": model_id,
                    "kind": "pose_set",
                    "id": str(pose_set.id),
                    "batch_id": str(batch.id),
                    "status": "running",
                    "error_code": None,
                }
            )
        for ref in refs:
            if ref.get("status") != "running" or not ref.get("batch_id"):
                continue
            batch = await self._batches.get_by_id_and_mayorista(
                UUID(ref["batch_id"]), photoshoot.mayorista_id
            )
            if batch is None:
                continue
            items_busy = any(
                item.status in {"pending", "processing"} for item in batch.items
            )
            if items_busy:
                continue
            if batch.status == "failed" or (
                batch.items and all(item.status == "failed" for item in batch.items)
            ):
                ref["status"] = "failed"
                ref["error_code"] = "POSE_SET_FAILED"
            else:
                ref["status"] = "completed"
        stage.external_refs = refs
        flag_modified(stage, "external_refs")
        living = self._living_model_ids(photoshoot)
        decided = [ref for ref in refs if ref.get("model_id") in living]
        if living and decided and all(
            ref.get("status") in {"completed", "failed"} for ref in decided
        ):
            if any(ref.get("status") == "completed" for ref in decided):
                stage.status = "completed"
                logger.info(
                    "stage_completed",
                    extra={"photoshoot_id": str(photoshoot.id), "stage": "poses"},
                )
            else:
                stage.status = "failed"
                stage.error_code = "POSE_SET_FAILED"
                logger.warning(
                    "stage_failed",
                    extra={
                        "photoshoot_id": str(photoshoot.id),
                        "stage": "poses",
                        "error_code": "POSE_SET_FAILED",
                    },
                )
            stage.completed_at = datetime.now(timezone.utc)

    async def _materialize_ready(
        self, photoshoot: Photoshoot, stage: PhotoshootStage | None, config: dict
    ) -> None:
        if stage is None:
            return
        pose_by_photo = {
            item["model_photo_id"]: (model_id, item["pose"])
            for model_id, items in (config.get("resolved_poses") or {}).items()
            for item in items
        }
        for ref in stage.external_refs or []:
            batch_id = ref.get("batch_id")
            if not batch_id:
                continue
            batch = await self._batches.get_by_id_and_mayorista(
                UUID(batch_id), photoshoot.mayorista_id
            )
            if batch is None:
                continue
            for item in batch.items:
                if item.status != "complete" or not item.result_media_id:
                    continue
                media = await self._media.get_by_id(
                    item.result_media_id, photoshoot.mayorista_id
                )
                if media is None:
                    continue
                mapping = pose_by_photo.get(str(item.model_id))
                if mapping is None:
                    continue
                model_id, pose = mapping
                await self._materializer.materialize_slot(
                    photoshoot,
                    model_id=UUID(model_id),
                    pose_id=item.model_id,
                    pose=pose,
                    source_key=media.minio_key,
                )

    async def _advance_composition(
        self, photoshoot: Photoshoot, stage: PhotoshootStage | None, config: dict
    ) -> None:
        if stage is None or stage.status in {"skipped", "completed", "failed"}:
            return
        overlay = config.get("overlay")
        if not overlay:
            stage.status = "skipped"
            stage.completed_at = datetime.now(timezone.utc)
            logger.info(
                "stage_skipped",
                extra={"photoshoot_id": str(photoshoot.id), "stage": "composition"},
            )
            return
        poses = next(s for s in photoshoot.stages if s.name == "poses")
        if poses.status not in {"completed", "failed"}:
            return
        if stage.status == "pending":
            stage.status = "running"
            stage.started_at = datetime.now(timezone.utc)
            logger.info(
                "stage_started",
                extra={"photoshoot_id": str(photoshoot.id), "stage": "composition"},
            )
        photoshoot = await self._repo.get(photoshoot.id) or photoshoot
        request = _composition_request(overlay)
        pending = False
        for result in photoshoot.results:
            existing = await self._overlays.get_by_generation_job_id(
                result.generation_job_id
            )
            if existing is not None:
                continue
            try:
                await self._composition.compose(
                    photoshoot.mayorista_id, result.generation_job_id, request
                )
            except OverlayDoesNotFitError:
                logger.warning(
                    "overlay_blocked",
                    extra={"generation_job_id": str(result.generation_job_id)},
                )
            except Exception:
                pending = True
                logger.warning(
                    "composition_failed",
                    extra={"generation_job_id": str(result.generation_job_id)},
                )
        if not pending:
            stage.status = "completed"
            stage.completed_at = datetime.now(timezone.utc)
            logger.info(
                "stage_completed",
                extra={"photoshoot_id": str(photoshoot.id), "stage": "composition"},
            )


def _composition_request(overlay: dict) -> CompositionRequest:
    kwargs: dict = {"sku": overlay["text"]}
    placement = overlay.get("placement")
    style = overlay.get("style")
    if isinstance(placement, dict):
        kwargs["placement"] = OverlayPlacement.model_validate(placement)
    if isinstance(style, dict):
        kwargs["style"] = OverlayStyle.model_validate(style)
    return CompositionRequest(**kwargs)


def build_orchestration_service(db: AsyncSession) -> PhotoshootOrchestrationService:
    repo = PhotoshootRepository(db)
    jobs = GenerationJobRepository(db)
    garments = GarmentPhotoRepo(db)
    photos = ModelPhotoRepo(db)
    media = MediaItemRepo(db)
    batches = BatchJobRepo(db)
    vton = VTONJobService(VTONJobRepo(db), garments, photos, None)
    batch_submit = BatchSubmissionService(batches, garments, photos, vton)
    storage = StorageService()
    return PhotoshootOrchestrationService(
        db=db,
        repo=repo,
        tryoff=TryoffJobService(TryoffJobRepo(db), SourceImageRepo(db), MinIOClient()),
        tryoff_jobs=TryoffJobRepo(db),
        vton=vton,
        poses=PoseSetSubmissionService(
            PoseSetRepo(db),
            ModelRepo(db),
            photos,
            garments,
            batches,
            batch_submit,
            db,
        ),
        batches=batches,
        batch_submit=batch_submit,
        media=media,
        garments=garments,
        garment_upload=MediaUploadService(garments, photos, MinIOClient()),
        materializer=PhotoshootMaterializationService(repo, jobs, storage),
        composition=SkuCompositionService(
            ProductOverlayRepository(db),
            CompositionVersionRepository(db),
            jobs,
            CompositionSnapshotRepository(db),
            storage,
        ),
        overlays=ProductOverlayRepository(db),
        storage=storage,
    )

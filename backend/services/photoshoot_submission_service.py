"""Accept a Contract-C photoshoot (FR-5). Does not wait for stages."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_app import app as celery_app
from core.config import settings
from models.photoshoot import Photoshoot, PhotoshootStage
from models.service_client import ServiceClient
from repositories.bridge_source_image_repo import BridgeSourceImageRepository
from repositories.image_template_repo import ImageTemplateRepository
from repositories.media_repo import ModelPhotoRepo
from repositories.model_repo import ModelRepo
from repositories.photoshoot_repo import PhotoshootRepository
from services.composition_spec import InvalidSkuError, SKU_MAX_LENGTH, normalize_sku
from services.credential_gate_service import CredentialGateService, CredentialMissingError
from services.model_pose_service import VALID_POSES
from services.photoshoot_errors import (
    PhotoshootCredentialMissingError,
    PhotoshootKindMismatchError,
    PhotoshootModelUnavailableError,
    PhotoshootOverlayTooLongError,
    PhotoshootPoseInvalidError,
    PhotoshootProductNotFoundError,
    PhotoshootSourceForbiddenError,
    PhotoshootSourceNotReadyError,
    PhotoshootTemplateError,
    PhotoshootValidationError,
    PhotoshootVariantUnsupportedError,
)
from services.photoshoot_pipeline_policy import plan as plan_stages
from services.product_link_service import ProductLinkError, ProductLinkService
from services.staff_identity_service import StaffIdentityService

logger = logging.getLogger(__name__)

CLOTH_TYPES = ("upper_body", "lower_body", "dress")
_POSE_RANK = {pose: index for index, pose in enumerate(VALID_POSES)}


@dataclass
class PhotoshootSubmitResult:
    photoshoot: Photoshoot
    stages: list[PhotoshootStage]
    external_product_id: str


def _fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


class PhotoshootSubmissionService:
    def __init__(
        self,
        db: AsyncSession,
        repo: PhotoshootRepository,
        links: ProductLinkService,
        staff: StaffIdentityService,
        sources: BridgeSourceImageRepository,
        models: ModelRepo,
        photos: ModelPhotoRepo,
        templates: ImageTemplateRepository,
        credentials: CredentialGateService,
    ) -> None:
        self._db = db
        self._repo = repo
        self._links = links
        self._staff = staff
        self._sources = sources
        self._models = models
        self._photos = photos
        self._templates = templates
        self._credentials = credentials

    async def submit(
        self,
        *,
        client: ServiceClient,
        external_product_id: str,
        staff_id: UUID,
        source_image_id: UUID,
        input_kind: str,
        model_ids: list[UUID],
        cloth_type: str,
        pose_ids: list[str] | None,
        pose_count: int | None,
        template_id: UUID | None,
        background: str | None,
        colors,
        overlay: dict | None,
        variant_key: str | None,
        external_wholesaler_id: str | None,
        idempotency_key: str | None,
    ) -> PhotoshootSubmitResult:
        if variant_key is not None:
            raise PhotoshootVariantUnsupportedError("variant_key is reserved and must be null")
        if pose_ids is not None and pose_count is not None:
            raise PhotoshootPoseInvalidError("pose_ids and pose_count are mutually exclusive")
        if cloth_type not in CLOTH_TYPES:
            raise PhotoshootValidationError("Unknown cloth_type")
        if not model_ids or len(set(model_ids)) != len(model_ids):
            raise PhotoshootValidationError("model_ids must be a non-empty unique list")

        overlay_spec = _normalize_overlay(overlay)

        await self._staff.resolve_staff_identity(client, staff_id)
        try:
            link = await self._links.resolve_active_link(
                client.system,
                external_product_id,
                external_wholesaler_id,
                client.tenant_id,
            )
        except ProductLinkError as exc:
            raise PhotoshootProductNotFoundError("Product link not found") from exc

        source = await self._sources.get_owned(
            source_image_id, link.id, client.tenant_id
        )
        if source is None:
            raise PhotoshootSourceForbiddenError("Source image is not available")
        if source.status != "ready":
            raise PhotoshootSourceNotReadyError("Source image is not ready")
        if source.kind != input_kind:
            raise PhotoshootKindMismatchError("Source image kind does not match input_kind")

        if template_id is not None:
            template = await self._templates.is_selectable_for(template_id, link.mayorista_id)
            if template is None or template.status != "active":
                raise PhotoshootTemplateError("Template is not selectable")

        resolved_poses, pose_types = await self._resolve_poses(
            link.mayorista_id, model_ids, pose_ids, pose_count
        )
        expected = len(model_ids) * len(pose_types)
        if expected < 1:
            raise PhotoshootPoseInvalidError("expected_results must be at least 1")

        try:
            self._credentials.require("replicate")
        except CredentialMissingError as exc:
            raise PhotoshootCredentialMissingError(
                "Image generation is unavailable: replicate is not configured"
            ) from exc

        has_overlay = overlay_spec is not None
        stage_plan = plan_stages(input_kind, has_overlay)
        garment_id = (
            str(source.registered_media_id)
            if input_kind == "flat_garment" and source.registered_media_id
            else None
        )
        configuration = {
            "input_kind": input_kind,
            "source_image_id": str(source.id),
            "registered_media_id": (
                str(source.registered_media_id) if source.registered_media_id else None
            ),
            "registered_media_kind": source.registered_media_kind,
            "template_id": str(template_id) if template_id else None,
            "cloth_type": cloth_type,
            "background": background,
            "colors": colors,
            "overlay": overlay_spec,
            "model_ids": [str(mid) for mid in model_ids],
            "pose_types": list(pose_types),
            "resolved_poses": resolved_poses,
            "garment_id_effective": garment_id,
            "tick_count": 0,
        }
        photoshoot = Photoshoot(
            id=uuid4(),
            product_link_id=link.id,
            staff_id=staff_id,
            source_image_id=source.id,
            tenant_id=client.tenant_id,
            mayorista_id=link.mayorista_id,
            input_kind=input_kind,
            configuration=configuration,
            status="queued",
            expected_results=expected,
            idempotency_key=idempotency_key,
            payload_fingerprint=_fingerprint(
                {
                    "source_image_id": str(source_image_id),
                    "input_kind": input_kind,
                    "model_ids": [str(m) for m in model_ids],
                    "pose_types": list(pose_types),
                    "cloth_type": cloth_type,
                }
            ),
            variant_key=None,
        )
        stages = [
            PhotoshootStage(
                photoshoot_id=photoshoot.id,
                name=item.name,
                status=item.status,
                external_refs=[],
            )
            for item in stage_plan
        ]
        await self._repo.add_aggregate(photoshoot, stages)
        await self._db.commit()
        await self._db.refresh(photoshoot)
        logger.info(
            "photoshoot_accepted",
            extra={
                "photoshoot_id": str(photoshoot.id),
                "input_kind": input_kind,
                "expected_results": expected,
                "tenant_id": str(client.tenant_id),
            },
        )
        try:
            celery_app.send_task(
                "tasks.photoshoot_orchestration.photoshoot_tick_task",
                args=[str(photoshoot.id)],
                queue="photoshoot",
            )
            logger.info(
                "photoshoot_enqueued",
                extra={
                    "photoshoot_id": str(photoshoot.id),
                    "tenant_id": str(client.tenant_id),
                },
            )
        except Exception:
            logger.warning(
                "photoshoot_enqueue_failed",
                extra={"photoshoot_id": str(photoshoot.id)},
            )
        return PhotoshootSubmitResult(photoshoot, stages, external_product_id)

    async def _resolve_poses(
        self,
        mayorista_id: UUID,
        model_ids: list[UUID],
        pose_ids: list[str] | None,
        pose_count: int | None,
    ) -> tuple[dict[str, list[dict]], tuple[str, ...]]:
        per_model: dict[UUID, dict[str, UUID]] = {}
        for model_id in model_ids:
            model = await self._models.get_by_id(model_id, mayorista_id)
            if model is None:
                raise PhotoshootModelUnavailableError("Model is not available")
            photos = await self._photos.list_by_model(model_id)
            owned = [
                photo
                for photo in photos
                if photo.pose
                and (photo.is_curated or photo.mayorista_id == mayorista_id)
            ]
            per_model[model_id] = {photo.pose: photo.id for photo in owned}

        common = set.intersection(*(set(mapping) for mapping in per_model.values()))
        if pose_ids is not None:
            requested = tuple(pose_ids)
            if not requested or len(set(requested)) != len(requested):
                raise PhotoshootPoseInvalidError("pose_ids must be unique and non-empty")
            unknown = [pose for pose in requested if pose not in VALID_POSES]
            if unknown:
                raise PhotoshootPoseInvalidError("pose_ids must be front, side, or back")
            missing = [pose for pose in requested if pose not in common]
            if missing:
                raise PhotoshootPoseInvalidError("Every model must have the requested poses")
            pose_types = requested
        else:
            count = pose_count or settings.PHOTOSHOOT_DEFAULT_POSE_COUNT
            if count < 1 or count > 3:
                raise PhotoshootPoseInvalidError("pose_count must be between 1 and 3")
            available = tuple(
                pose for pose in VALID_POSES if pose in common
            )
            if len(available) < count:
                raise PhotoshootPoseInvalidError(
                    "Not every model has enough poses for the requested count"
                )
            pose_types = available[:count]

        resolved = {
            str(model_id): [
                {"pose": pose, "model_photo_id": str(per_model[model_id][pose])}
                for pose in pose_types
            ]
            for model_id in model_ids
        }
        return resolved, pose_types


def _normalize_overlay(overlay: dict | None) -> dict | None:
    if not overlay:
        return None
    text = str(overlay.get("text") or "").strip()
    if not text:
        return None
    try:
        normalized = normalize_sku(text)
    except InvalidSkuError as exc:
        raise PhotoshootOverlayTooLongError(str(exc)) from exc
    if len(normalized) > SKU_MAX_LENGTH:
        raise PhotoshootOverlayTooLongError(
            f"SKU exceeds {SKU_MAX_LENGTH} characters"
        )
    return {
        "text": normalized,
        "placement": overlay.get("placement"),
        "style": overlay.get("style"),
    }


def build_submission_service(db: AsyncSession) -> PhotoshootSubmissionService:
    from repositories.mayorista_repo import MayoristaRepository
    from repositories.product_link_repo import ProductLinkRepository
    from repositories.staff_identity_link_repo import StaffIdentityLinkRepository

    staff = StaffIdentityService(
        db,
        StaffIdentityLinkRepository(db),
        MayoristaRepository(db),
    )
    return PhotoshootSubmissionService(
        db=db,
        repo=PhotoshootRepository(db),
        links=ProductLinkService(ProductLinkRepository(db)),
        staff=staff,
        sources=BridgeSourceImageRepository(db),
        models=ModelRepo(db),
        photos=ModelPhotoRepo(db),
        templates=ImageTemplateRepository(db),
        credentials=CredentialGateService(),
    )

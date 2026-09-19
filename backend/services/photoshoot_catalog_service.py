"""Read-only photoshoot options catalog for the BFashion bridge (ADR-063)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from models.image_template import ImageTemplate
from models.media import ModelPhoto
from models.model import Model
from models.service_client import ServiceClient
from models.vton_job import ClothType
from repositories.image_template_repo import ImageTemplateRepository
from repositories.media_repo import ModelPhotoRepo
from repositories.model_repo import ModelRepo
from services.model_pose_service import VALID_POSES
from services.product_link_service import ProductLinkError, ProductLinkService

logger = logging.getLogger(__name__)

CATALOG_VERSION_SALT = "photoshoot-options:v1"
MAX_POSE_COUNT = len(VALID_POSES)
CLOTH_TYPE_VALUES = tuple(item.value for item in ClothType)
CLOTH_TYPE_LABELS = {
    "upper_body": "Upper body",
    "lower_body": "Lower body",
    "dress": "Dress",
}
_POSE_RANK = {pose: index for index, pose in enumerate(VALID_POSES)}


class PhotoshootCatalogError(Exception):
    """Base error for the photoshoot options catalog."""

    code = "PHOTOSHOOT_CATALOG_ERROR"
    status_code = 400

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class PhotoshootCatalogNotVisibleError(PhotoshootCatalogError):
    """Product link is missing, inactive, or not operable by this client."""

    code = "PRODUCT_LINK_NOT_FOUND"
    status_code = 404


@dataclass(frozen=True)
class CatalogTemplateRow:
    id: UUID
    name: str
    scope: str
    wholesaler_scope: UUID | None
    version: int
    model: str | None
    background: str | None
    colors: Any
    rack: str | None
    updated_at: datetime


@dataclass(frozen=True)
class CatalogModelRow:
    id: UUID
    name: str
    available_poses: tuple[str, ...]
    preview_url: str | None
    preview_minio_key: str | None


@dataclass(frozen=True)
class ClothTypeOption:
    value: str
    label: str


@dataclass(frozen=True)
class PhotoshootOptionsCatalog:
    templates: tuple[CatalogTemplateRow, ...]
    models: tuple[CatalogModelRow, ...]
    cloth_types: tuple[ClothTypeOption, ...]
    background_suggestions: tuple[str, ...]
    color_suggestions: tuple[str, ...]
    max_pose_count: int
    catalog_version: str


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _color_values(colors: Any) -> list[str]:
    if colors is None:
        return []
    if isinstance(colors, str):
        stripped = colors.strip()
        return [stripped] if stripped else []
    if isinstance(colors, list):
        values: list[str] = []
        for item in colors:
            if isinstance(item, str) and item.strip():
                values.append(item)
        return values
    return []


def compute_catalog_version(
    templates: list[ImageTemplate],
    models: list[Model],
    photos_by_model: dict[UUID, list[ModelPhoto]],
) -> str:
    """Deterministic hash of the visible set (ADR-063)."""
    template_payload = [
        {
            "id": str(template.id),
            "scope": template.scope,
            "updated_at": _iso(template.updated_at),
            "version": int(template.version),
        }
        for template in sorted(templates, key=lambda item: str(item.id))
    ]
    model_payload = []
    for model in sorted(models, key=lambda item: str(item.id)):
        photos = [
            photo
            for photo in photos_by_model.get(model.id, [])
            if photo.pose and photo.model_id
        ]
        photos.sort(key=lambda photo: (_POSE_RANK.get(photo.pose, 99), str(photo.id)))
        model_payload.append(
            {
                "id": str(model.id),
                "photos": [
                    {
                        "photo_id": str(photo.id),
                        "pose": photo.pose,
                        "uploaded_at": _iso(photo.uploaded_at),
                    }
                    for photo in photos
                ],
            }
        )
    payload = {
        "cloth_types": list(CLOTH_TYPE_VALUES),
        "max_pose_count": MAX_POSE_COUNT,
        "models": model_payload,
        "templates": template_payload,
        "v": CATALOG_VERSION_SALT,
    }
    encoded = json.dumps(
        payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()[:32]}"


class PhotoshootCatalogService:
    def __init__(
        self,
        product_links: ProductLinkService,
        templates: ImageTemplateRepository,
        models: ModelRepo,
        photos: ModelPhotoRepo,
        minio: Any,
    ) -> None:
        self._product_links = product_links
        self._templates = templates
        self._models = models
        self._photos = photos
        self._minio = minio

    async def get_photoshoot_options(
        self,
        client: ServiceClient,
        external_product_id: str,
        external_wholesaler_id: str | None = None,
    ) -> PhotoshootOptionsCatalog:
        try:
            link = await self._product_links.resolve_active_link(
                client.system,
                external_product_id,
                external_wholesaler_id,
                client.tenant_id,
            )
        except ProductLinkError:
            logger.warning(
                "photoshoot_catalog_not_visible",
                extra={
                    "system": client.system,
                    "tenant_id": str(client.tenant_id),
                    "external_product_id": external_product_id,
                },
            )
            raise PhotoshootCatalogNotVisibleError("Product link not found") from None

        owner_id = link.mayorista_id
        selectable, models = await asyncio.gather(
            self._templates.list_selectable(owner_id),
            self._models.list_by_mayorista(owner_id),
        )
        templates = [
            template
            for template in selectable
            if template.status == "active"
            and (
                template.scope == "common"
                or (
                    template.scope == "private"
                    and template.wholesaler_id == owner_id
                )
            )
        ]
        photos_by_model = await self._photos.list_by_model_ids(
            [model.id for model in models]
        )
        catalog_version = compute_catalog_version(
            templates, models, photos_by_model
        )

        template_rows = tuple(
            self._to_template_row(template)
            for template in sorted(
                templates,
                key=lambda item: (
                    0 if item.scope == "common" else 1,
                    item.name.lower(),
                    str(item.id),
                ),
            )
        )
        model_rows = tuple(
            self._to_model_row(model, photos_by_model.get(model.id, []))
            for model in sorted(
                models, key=lambda item: (item.name.lower(), str(item.id))
            )
        )
        backgrounds = sorted(
            {
                template.background.strip()
                for template in templates
                if isinstance(template.background, str) and template.background.strip()
            }
        )
        colors = sorted(
            {
                value
                for template in templates
                for value in _color_values(template.colors)
            }
        )
        catalog = PhotoshootOptionsCatalog(
            templates=template_rows,
            models=model_rows,
            cloth_types=tuple(
                ClothTypeOption(value=value, label=CLOTH_TYPE_LABELS[value])
                for value in CLOTH_TYPE_VALUES
            ),
            background_suggestions=tuple(backgrounds),
            color_suggestions=tuple(colors),
            max_pose_count=MAX_POSE_COUNT,
            catalog_version=catalog_version,
        )
        logger.info(
            "photoshoot_catalog_served",
            extra={
                "tenant_id": str(client.tenant_id),
                "external_product_id": external_product_id,
                "mayorista_id": str(owner_id),
                "catalog_version": catalog_version,
                "template_count": len(template_rows),
                "model_count": len(model_rows),
            },
        )
        return catalog

    async def with_preview_urls(
        self, catalog: PhotoshootOptionsCatalog
    ) -> PhotoshootOptionsCatalog:
        """Sign preview URLs only after the router decides this is a 200."""
        signed: list[CatalogModelRow] = []
        for row in catalog.models:
            preview_url = None
            if row.preview_minio_key:
                preview_url = await self._minio.get_presigned_url(
                    bucket="originals", key=row.preview_minio_key
                )
            signed.append(
                replace(row, preview_url=preview_url, preview_minio_key=None)
            )
        return replace(catalog, models=tuple(signed))

    @staticmethod
    def _to_template_row(template: ImageTemplate) -> CatalogTemplateRow:
        wholesaler_scope = (
            template.wholesaler_id if template.scope == "private" else None
        )
        return CatalogTemplateRow(
            id=template.id,
            name=template.name,
            scope=template.scope,
            wholesaler_scope=wholesaler_scope,
            version=int(template.version),
            model=template.model,
            background=template.background,
            colors=template.colors,
            rack=template.rack,
            updated_at=template.updated_at,
        )

    @staticmethod
    def _to_model_row(model: Model, photos: list[ModelPhoto]) -> CatalogModelRow:
        posed = [photo for photo in photos if photo.pose and photo.model_id]
        posed.sort(key=lambda photo: _POSE_RANK.get(photo.pose, 99))
        available = tuple(photo.pose for photo in posed if photo.pose in _POSE_RANK)
        preview_key = posed[0].minio_key if posed else None
        return CatalogModelRow(
            id=model.id,
            name=model.name,
            available_poses=available,
            preview_url=None,
            preview_minio_key=preview_key,
        )

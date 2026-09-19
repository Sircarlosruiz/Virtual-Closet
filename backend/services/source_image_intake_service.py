"""Presign and confirm BFashion source-image uploads (ADR-061, ADR-062)."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.bridge_source_image import (
    SOURCE_IMAGE_CONTENT_TYPES,
    SOURCE_IMAGE_KINDS,
    BridgeSourceImage,
)
from models.product_link import ProductLink
from models.service_client import ServiceClient
from repositories.bridge_source_image_repo import BridgeSourceImageRepository
from repositories.media_repo import GarmentPhotoRepo
from repositories.tryoff_job_repo import SourceImageRepo
from services.media_service import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFileTypeError,
    MediaUploadService,
    _validate_file,
)
from services.product_link_service import ProductLinkError, ProductLinkService
from services.staff_identity_service import StaffIdentityService
from services.storage_service import StorageService
from services.tryoff_source_image_service import TryoffSourceImageService

logger = logging.getLogger(__name__)

_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class SourceImageIntakeError(Exception):
    """Base error for source-image intake."""

    code = "SOURCE_IMAGE_ERROR"
    status_code = 400

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class SourceImageValidationError(SourceImageIntakeError):
    """Declared kind, type, or size is invalid before signing."""

    code = "SOURCE_IMAGE_INVALID"
    status_code = 422


class SourceImageProductNotFoundError(SourceImageIntakeError):
    """Product link is missing, inactive, or not operable by this client."""

    code = "PRODUCT_LINK_NOT_FOUND"
    status_code = 404


class SourceImageForbiddenError(SourceImageIntakeError):
    """Reservation is missing or belongs to another product (ADR-061)."""

    code = "SOURCE_IMAGE_FORBIDDEN"
    status_code = 403


class SourceImageNotUploadedError(SourceImageIntakeError):
    """Object is not in storage yet; reservation stays pending."""

    code = "SOURCE_IMAGE_NOT_UPLOADED"
    status_code = 409


class SourceImageRejectedError(SourceImageIntakeError):
    """Reservation is or became rejected."""

    code = "SOURCE_IMAGE_REJECTED"
    status_code = 409


class StorageUnavailableError(SourceImageIntakeError):
    """Could not sign or observe storage."""

    code = "STORAGE_UNAVAILABLE"
    status_code = 503


@dataclass
class SourceImagePresignResult:
    reservation: BridgeSourceImage
    upload_url: str
    expires_in: int


@dataclass
class SourceImageConfirmResult:
    reservation: BridgeSourceImage
    preview_url: str | None


def _sanitize_filename(filename: str) -> str:
    name = filename.replace("\\", "/").split("/")[-1]
    cleaned = _UNSAFE_FILENAME.sub("-", name).strip(".-")
    return (cleaned or "upload")[:255]


def _detect_content_type(data: bytes) -> str | None:
    if data[:4] == b"\x89PNG":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    return None


def _media_filename(source_image_id: UUID, content_type: str) -> str:
    ext = "png" if content_type == "image/png" else "jpg"
    return f"{source_image_id}.{ext}"


class SourceImageIntakeService:
    def __init__(
        self,
        db: AsyncSession,
        reservations: BridgeSourceImageRepository,
        product_links: ProductLinkService,
        staff_identities: StaffIdentityService,
        storage: StorageService,
        tryoff_sources: TryoffSourceImageService,
        garments: MediaUploadService,
    ) -> None:
        self._db = db
        self._reservations = reservations
        self._product_links = product_links
        self._staff_identities = staff_identities
        self._storage = storage
        self._tryoff_sources = tryoff_sources
        self._garments = garments

    async def _resolve_link(
        self,
        client: ServiceClient,
        external_product_id: str,
        external_wholesaler_id: str | None,
    ) -> ProductLink:
        try:
            return await self._product_links.resolve_active_link(
                client.system,
                external_product_id,
                external_wholesaler_id,
                client.tenant_id,
            )
        except ProductLinkError as exc:
            raise SourceImageProductNotFoundError(
                "Product link not found"
            ) from exc

    async def presign(
        self,
        client: ServiceClient,
        external_product_id: str,
        staff_id: UUID,
        kind: str,
        content_type: str,
        size_bytes: int,
        filename: str,
        external_wholesaler_id: str | None = None,
    ) -> SourceImagePresignResult:
        if kind not in SOURCE_IMAGE_KINDS:
            raise SourceImageValidationError(
                "kind must be garment_on_model or flat_garment",
                context={"kind": kind},
            )
        if content_type not in SOURCE_IMAGE_CONTENT_TYPES:
            raise SourceImageValidationError(
                "content_type must be image/jpeg or image/png",
                context={"content_type": content_type},
            )
        max_bytes = settings.BRIDGE_SOURCE_IMAGE_MAX_BYTES
        if size_bytes < 1 or size_bytes > max_bytes:
            raise SourceImageValidationError(
                "size_bytes is outside the allowed range",
                context={"size_bytes": size_bytes, "max_bytes": max_bytes},
            )

        staff = await self._staff_identities.resolve_staff_identity(
            client, staff_id
        )
        link = await self._resolve_link(
            client, external_product_id, external_wholesaler_id
        )

        source_image_id = uuid4()
        storage_key = (
            f"bridge/source-images/{link.id}/{source_image_id}"
        )
        _sanitize_filename(filename)
        reservation = BridgeSourceImage(
            id=source_image_id,
            product_link_id=link.id,
            staff_id=staff.id,
            tenant_id=client.tenant_id,
            kind=kind,
            storage_key=storage_key,
            declared_content_type=content_type,
            declared_size_bytes=size_bytes,
            status="pending",
        )
        await self._reservations.add(reservation)

        ttl = settings.BRIDGE_SOURCE_IMAGE_UPLOAD_TTL_SECONDS
        try:
            upload_url = await self._storage.generate_upload_url(
                storage_key,
                ttl_seconds=ttl,
                bucket_override="originals",
                content_type=content_type,
            )
        except Exception as exc:
            await self._db.rollback()
            raise StorageUnavailableError(
                "Storage is unavailable"
            ) from exc

        await self._db.commit()
        await self._db.refresh(reservation)
        logger.info(
            "source_image_reserved",
            extra={
                "source_image_id": str(reservation.id),
                "product_link_id": str(link.id),
                "kind": kind,
                "tenant_id": str(client.tenant_id),
                "status": "pending",
            },
        )
        return SourceImagePresignResult(reservation, upload_url, ttl)

    async def confirm(
        self,
        client: ServiceClient,
        external_product_id: str,
        source_image_id: UUID,
        staff_id: UUID,
        checksum_sha256: str | None = None,
        external_wholesaler_id: str | None = None,
    ) -> SourceImageConfirmResult:
        await self._staff_identities.resolve_staff_identity(client, staff_id)
        link = await self._resolve_link(
            client, external_product_id, external_wholesaler_id
        )
        locked = await self._reservations.lock_owned(
            source_image_id, link.id, client.tenant_id
        )
        if locked is None:
            raise SourceImageForbiddenError("Source image not found")
        if locked.status == "rejected":
            raise SourceImageRejectedError(
                locked.rejection_reason or "Source image was rejected",
                context={
                    "source_image_id": str(locked.id),
                    "status": "rejected",
                },
            )
        if locked.status == "ready":
            return await self._replay_ready(locked)

        head = await self._storage.head_object(
            locked.storage_key, bucket_override="originals"
        )
        if head is None:
            raise SourceImageNotUploadedError(
                "Source image has not been uploaded yet",
                context={"source_image_id": str(locked.id)},
            )

        try:
            data = await self._storage.get_object_bytes(
                locked.storage_key, bucket_override="originals"
            )
        except Exception as exc:
            raise StorageUnavailableError("Storage is unavailable") from exc

        reject_code = self._evaluate_object(
            locked, head, data, checksum_sha256
        )
        if reject_code is not None:
            actual_type = _detect_content_type(data)
            await self._reservations.transition_pending_to_rejected(
                locked.id,
                reason=reject_code,
                actual_content_type=actual_type,
                actual_size_bytes=len(data),
            )
            await self._db.commit()
            logger.warning(
                "source_image_rejected",
                extra={
                    "source_image_id": str(locked.id),
                    "code": reject_code,
                    "product_link_id": str(link.id),
                },
            )
            raise SourceImageRejectedError(
                self._rejection_message(reject_code),
                context={
                    "source_image_id": str(locked.id),
                    "status": "rejected",
                    "reason": reject_code,
                },
            )

        actual_type = _detect_content_type(data) or locked.declared_content_type
        media_kind, media_id = await self._register_media(
            locked, link, actual_type, len(data)
        )
        updated = await self._reservations.transition_pending_to_ready(
            locked.id,
            actual_content_type=actual_type,
            actual_size_bytes=len(data),
            registered_media_id=media_id,
            registered_media_kind=media_kind,
        )
        if not updated:
            await self._db.rollback()
            raced = await self._reservations.get_owned(
                source_image_id, link.id, client.tenant_id
            )
            if raced is None:
                raise SourceImageForbiddenError("Source image not found")
            if raced.status == "ready":
                return await self._replay_ready(raced)
            raise SourceImageRejectedError(
                raced.rejection_reason or "Source image was rejected",
                context={
                    "source_image_id": str(raced.id),
                    "status": raced.status,
                },
            )

        await self._db.commit()
        ready = await self._reservations.get_owned(
            source_image_id, link.id, client.tenant_id
        )
        if ready is None:
            raise SourceImageForbiddenError("Source image not found")
        logger.info(
            "source_image_ready",
            extra={
                "source_image_id": str(ready.id),
                "kind": ready.kind,
                "product_link_id": str(link.id),
                "tenant_id": str(client.tenant_id),
                "status": "ready",
            },
        )
        return await self._replay_ready(ready)

    async def _replay_ready(
        self, reservation: BridgeSourceImage
    ) -> SourceImageConfirmResult:
        preview_url = await self._storage.generate_download_url(
            reservation.storage_key,
            ttl_seconds=settings.BRIDGE_SOURCE_IMAGE_PREVIEW_TTL_SECONDS,
            bucket_override="originals",
        )
        logger.info(
            "source_image_confirm_replayed",
            extra={
                "source_image_id": str(reservation.id),
                "kind": reservation.kind,
                "status": reservation.status,
            },
        )
        return SourceImageConfirmResult(reservation, preview_url)

    def _evaluate_object(
        self,
        reservation: BridgeSourceImage,
        head: dict,
        data: bytes,
        checksum_sha256: str | None,
    ) -> str | None:
        size = len(data)
        head_size = int(head.get("content_length") or 0)
        if size == 0 or head_size == 0:
            return "OBJECT_EMPTY"
        max_bytes = settings.BRIDGE_SOURCE_IMAGE_MAX_BYTES
        if size > max_bytes or head_size > max_bytes:
            return "OBJECT_TOO_LARGE"
        if size != reservation.declared_size_bytes or head_size != size:
            return "SIZE_MISMATCH"

        detected = _detect_content_type(data)
        head_type = head.get("content_type")
        if detected is None:
            return "UNREADABLE_IMAGE"
        if detected != reservation.declared_content_type:
            return "CONTENT_TYPE_MISMATCH"
        if (
            head_type
            and head_type in SOURCE_IMAGE_CONTENT_TYPES
            and head_type != reservation.declared_content_type
        ):
            return "CONTENT_TYPE_MISMATCH"

        try:
            _validate_file(data, detected)
        except EmptyFileError:
            return "OBJECT_EMPTY"
        except FileTooLargeError:
            return "OBJECT_TOO_LARGE"
        except InvalidFileTypeError:
            return "UNREADABLE_IMAGE"

        if checksum_sha256:
            digest = hashlib.sha256(data).hexdigest()
            if digest.lower() != checksum_sha256.strip().lower():
                return "CHECKSUM_MISMATCH"
        return None

    def _rejection_message(self, code: str) -> str:
        messages = {
            "OBJECT_EMPTY": "The uploaded file is empty",
            "OBJECT_TOO_LARGE": "The uploaded file exceeds the size limit",
            "SIZE_MISMATCH": "The uploaded file size does not match the declared size",
            "CONTENT_TYPE_MISMATCH": (
                "The uploaded file type does not match the declared type"
            ),
            "UNREADABLE_IMAGE": "The uploaded file is not a readable image",
            "CHECKSUM_MISMATCH": "The uploaded file checksum does not match",
        }
        return messages.get(code, "The uploaded file was rejected")

    async def _register_media(
        self,
        reservation: BridgeSourceImage,
        link: ProductLink,
        content_type: str,
        size_bytes: int,
    ) -> tuple[str, UUID]:
        filename = _media_filename(reservation.id, content_type)
        if reservation.kind == "garment_on_model":
            media = await self._tryoff_sources.register_existing(
                mayorista_id=link.mayorista_id,
                minio_key=reservation.storage_key,
                filename=filename,
                content_type=content_type,
                size_bytes=size_bytes,
            )
            return "source_image", media.id
        media = await self._garments.register_existing_garment(
            mayorista_id=link.mayorista_id,
            tenant_id=link.tenant_id,
            minio_key=reservation.storage_key,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        return "garment_photo", media.id


def build_intake_service(db: AsyncSession) -> SourceImageIntakeService:
    from core.minio_client import MinIOClient
    from repositories.mayorista_repo import MayoristaRepository
    from repositories.media_repo import ModelPhotoRepo
    from repositories.product_link_repo import ProductLinkRepository
    from repositories.staff_identity_link_repo import StaffIdentityLinkRepository

    staff = StaffIdentityService(
        db,
        StaffIdentityLinkRepository(db),
        MayoristaRepository(db),
    )
    return SourceImageIntakeService(
        db=db,
        reservations=BridgeSourceImageRepository(db),
        product_links=ProductLinkService(ProductLinkRepository(db)),
        staff_identities=staff,
        storage=StorageService(),
        tryoff_sources=TryoffSourceImageService(
            SourceImageRepo(db), MinIOClient()
        ),
        garments=MediaUploadService(
            GarmentPhotoRepo(db),
            ModelPhotoRepo(db),
            MinIOClient(),
        ),
    )

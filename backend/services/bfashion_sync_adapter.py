"""Outbound BFashion product-image ingest adapter.

Virtual Closet never exposes OpenAI credentials here. The adapter sends a
durable storage key plus a freshly minted transfer URL so an expired preview
URL can be recovered without regenerating the image.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx

from core.config import settings
from services.retry_policy import is_retriable_error
from services.storage_service import StorageService

_GENERATED_BUCKET = "generated"
_TRANSFER_TTL_SECONDS = 900


class BFashionSyncError(Exception):
    """Raised when the BFashion ingest call fails."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class BFashionImageIngest:
    external_product_id: str
    publication_selection_id: UUID
    generation_job_id: UUID
    composition_version_id: UUID | None
    durable_object_key: str
    content_type: str
    configuration: dict
    staff_id: UUID | None


@dataclass(frozen=True)
class BFashionImageResult:
    external_ref: str


class BFashionSyncAdapter(Protocol):
    async def upsert_product_image(
        self, payload: BFashionImageIngest
    ) -> BFashionImageResult:
        """Create or return the existing BFashion ProductImage for this selection."""


class HttpBFashionSyncAdapter:
    """HTTP client for BFashion's internal product-image ingest contract."""

    def __init__(self, storage: StorageService | None = None) -> None:
        self._storage = storage or StorageService()

    async def upsert_product_image(
        self, payload: BFashionImageIngest
    ) -> BFashionImageResult:
        base_url = settings.BFASHION_BASE_URL.strip().rstrip("/")
        if not base_url:
            raise BFashionSyncError("BFashion is not configured", retryable=True)

        transfer_url = await self._storage.generate_download_url(
            payload.durable_object_key,
            ttl_seconds=_TRANSFER_TTL_SECONDS,
            bucket_override=_GENERATED_BUCKET,
        )
        headers = {
            "Idempotency-Key": str(payload.publication_selection_id),
            "Content-Type": "application/json",
        }
        if settings.BFASHION_SERVICE_ID.strip():
            headers["X-Service-Id"] = settings.BFASHION_SERVICE_ID.strip()
        if settings.BFASHION_SERVICE_SECRET.strip():
            headers["X-Service-Secret"] = settings.BFASHION_SERVICE_SECRET.strip()

        url = f"{base_url}/internal/v1/products/{payload.external_product_id}/images"
        body = {
            "publication_selection_id": str(payload.publication_selection_id),
            "generation_job_id": str(payload.generation_job_id),
            "composition_version_id": (
                str(payload.composition_version_id)
                if payload.composition_version_id
                else None
            ),
            "storage_key": payload.durable_object_key,
            "transfer_url": transfer_url,
            "content_type": payload.content_type,
            "configuration": payload.configuration,
            "staff_id": str(payload.staff_id) if payload.staff_id else None,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, json=body, headers=headers)
                if response.status_code == 409:
                    data = response.json() if response.content else {}
                    ref = data.get("id") or str(payload.publication_selection_id)
                    return BFashionImageResult(external_ref=str(ref))
                response.raise_for_status()
                data = response.json() if response.content else {}
        except BFashionSyncError:
            raise
        except Exception as exc:
            raise BFashionSyncError(
                str(exc), retryable=is_retriable_error(exc)
            ) from exc

        ref = data.get("id") or str(payload.publication_selection_id)
        return BFashionImageResult(external_ref=str(ref))

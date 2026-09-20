"""Image-generation adapter that wraps CatVTONReplicateProvider (ADR-046)."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Mapping

from core.config import settings
from services.image_generation_providers import (
    ProviderInvocationResult,
    ProviderRequestError,
    ProviderTimeoutError,
)
from services.provider_timeout_policy import ProviderTimeoutPolicy
from services.storage_service import StorageService

_CLOTH_TYPE_MAP = {
    "upper_body": "upper",
    "lower_body": "lower",
    "dress": "overall",
    "upper": "upper",
    "lower": "lower",
    "overall": "overall",
}


class ReplicateTryOnAdapter:
    """Translates GenerationJob.input_data into CatVTONReplicateProvider.generate."""

    def __init__(
        self,
        inner=None,
        storage: StorageService | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self._inner = inner
        self._storage = storage or StorageService()
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else ProviderTimeoutPolicy().timeout_for("replicate").seconds
        )
        self.last_usage: dict[str, object] | None = None
        self.last_model: str | None = None

    async def generate(self, inputs: Mapping[str, object]) -> ProviderInvocationResult:
        self.last_usage = None
        self.last_model = None
        garment, model, cloth_type = await self._resolve_try_on_inputs(inputs)
        inner = self._inner
        if inner is None:
            from services.vton.catvton_replicate_provider import CatVTONReplicateProvider

            inner = CatVTONReplicateProvider()
        try:
            image_bytes = await asyncio.wait_for(
                inner.generate(garment, model, cloth_type),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise ProviderTimeoutError() from exc
        except ProviderTimeoutError:
            raise
        except ProviderRequestError:
            raise
        except Exception as exc:
            raise ProviderRequestError(f"Replicate try-on failed: {type(exc).__name__}") from exc

        inner_usage = getattr(inner, "last_usage", None)
        inner_model = getattr(inner, "last_model", None)
        self.last_usage = inner_usage if isinstance(inner_usage, dict) else None
        self.last_model = (
            inner_model
            if isinstance(inner_model, str) and inner_model.strip()
            else settings.CATVTON_REPLICATE_MODEL
        )
        return ProviderInvocationResult(
            image_bytes=image_bytes,
            provider_model=self.last_model,
            usage=self.last_usage,
        )

    async def _resolve_try_on_inputs(
        self, inputs: Mapping[str, object]
    ) -> tuple[bytes, bytes, str]:
        cloth_raw = str(inputs.get("cloth_type") or "").strip()
        cloth_type = _CLOTH_TYPE_MAP.get(cloth_raw)
        if not cloth_type:
            raise ProviderRequestError("try_on requires a supported cloth_type")

        garment = await self._load_bytes(
            inputs,
            bytes_key="garment_bytes",
            storage_key="garment_key",
            bucket_key="garment_bucket",
            default_bucket="originals",
            label="garment",
        )
        model = await self._load_bytes(
            inputs,
            bytes_key="model_bytes",
            storage_key="model_key",
            bucket_key="model_bucket",
            default_bucket="model-thumbnails",
            label="model",
        )
        return garment, model, cloth_type

    async def _load_bytes(
        self,
        inputs: Mapping[str, object],
        *,
        bytes_key: str,
        storage_key: str,
        bucket_key: str,
        default_bucket: str,
        label: str,
    ) -> bytes:
        raw = inputs.get(bytes_key)
        if isinstance(raw, (bytes, bytearray)) and raw:
            return bytes(raw)
        if isinstance(raw, str) and raw.strip():
            return base64.b64decode(raw)

        key = str(inputs.get(storage_key) or "").strip()
        if key:
            bucket = str(inputs.get(bucket_key) or default_bucket)
            return await self._storage.get_object_bytes(key, bucket_override=bucket)

        raise ProviderRequestError(f"try_on requires {label} bytes or storage key")

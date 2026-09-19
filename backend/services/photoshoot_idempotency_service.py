"""Photoshoot HTTP idempotency (ADR-071 / ADR-072).

Reuses ``compute_payload_fingerprint``. Does not call ``IdempotencyService``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from models.photoshoot import Photoshoot
from repositories.photoshoot_repo import PhotoshootRepository
from services.idempotency_service import compute_payload_fingerprint
from services.photoshoot_errors import PhotoshootIdempotencyConflictError

IdempotencyOutcomeKind = Literal["created", "replayed", "conflict", "unprotected"]


@dataclass(frozen=True)
class IdempotencyOutcome:
    kind: IdempotencyOutcomeKind
    photoshoot: Photoshoot | None = None
    fingerprint: str | None = None


def normalize_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def normalize_variant_key(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def photoshoot_fingerprint_payload(
    *,
    staff_id: UUID,
    source_image_id: UUID,
    input_kind: str,
    template_id: UUID | None,
    model_ids: list[UUID],
    pose_ids: list[str] | None,
    pose_count: int | None,
    cloth_type: str,
    background: str | None,
    colors,
    overlay: dict | None,
    variant_key: str | None,
    external_wholesaler_id: str | None,
) -> dict:
    return {
        "staff_id": str(staff_id),
        "source_image_id": str(source_image_id),
        "input_kind": input_kind,
        "template_id": str(template_id) if template_id else None,
        "model_ids": sorted(str(item) for item in model_ids),
        "pose_ids": sorted(pose_ids) if pose_ids is not None else None,
        "pose_count": pose_count,
        "cloth_type": cloth_type,
        "background": background,
        "colors": colors,
        "overlay": overlay,
        "variant_key": variant_key,
        "external_wholesaler_id": external_wholesaler_id,
    }


class PhotoshootIdempotencyService:
    def __init__(self, repo: PhotoshootRepository) -> None:
        self._repo = repo

    async def resolve(
        self,
        *,
        product_link_id: UUID,
        tenant_id: UUID,
        key: str | None,
        payload: dict,
    ) -> IdempotencyOutcome:
        if key is None:
            return IdempotencyOutcome(kind="unprotected")
        fingerprint = compute_payload_fingerprint(payload)
        existing = await self._repo.find_by_idempotency(
            product_link_id, tenant_id, key
        )
        if existing is None:
            return IdempotencyOutcome(kind="created", fingerprint=fingerprint)
        if existing.payload_fingerprint != fingerprint:
            raise PhotoshootIdempotencyConflictError(
                "Idempotency key already used with a different request payload"
            )
        return IdempotencyOutcome(
            kind="replayed",
            photoshoot=existing,
            fingerprint=fingerprint,
        )

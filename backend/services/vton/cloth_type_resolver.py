"""Resolve garment cloth_type without ML dependencies in the backend worker."""

import io

import httpx

from core.config import settings

_VALID = frozenset({"upper", "lower", "overall"})


def _normalize(cloth_type: str) -> str:
    value = (cloth_type or "upper").strip().lower()
    return value if value in _VALID else "upper"


def _classify_via_catvton(garment_bytes: bytes) -> str:
    url = f"{settings.CATVTON_LOCAL_URL.rstrip('/')}/classify"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            url,
            files={"garment": ("garment.jpg", io.BytesIO(garment_bytes), "image/jpeg")},
        )
        resp.raise_for_status()
        data = resp.json()
    return _normalize(str(data.get("cloth_type", "upper")))


def resolve_cloth_type(garment_bytes: bytes) -> str:
    """Classify garment type via CatVTON container, or use env default for other providers."""
    if settings.VTON_PROVIDER == "catvton_local":
        return _classify_via_catvton(garment_bytes)
    return _normalize(settings.CATVTON_CLOTH_TYPE)

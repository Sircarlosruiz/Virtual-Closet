"""Resolve garment cloth_type without ML dependencies in the backend worker."""

import io
import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_VALID = frozenset({"upper", "lower", "overall"})


def _normalize(cloth_type: str) -> str:
    value = (cloth_type or "upper").strip().lower()
    return value if value in _VALID else "upper"


def _heuristic_cloth_type(garment_bytes: bytes) -> str:
    from PIL import Image

    image = Image.open(io.BytesIO(garment_bytes)).convert("RGB")
    w, h = image.size
    ratio = h / max(w, 1)
    if ratio >= 1.25:
        return "overall"
    if ratio >= 0.95:
        return "upper"
    return "lower"


def _classify_via_server(base_url: str, garment_bytes: bytes) -> str:
    url = f"{base_url.rstrip('/')}/classify"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            url,
            files={"garment": ("garment.jpg", io.BytesIO(garment_bytes), "image/jpeg")},
        )
        resp.raise_for_status()
        data = resp.json()
    return _normalize(str(data.get("cloth_type", "upper")))


def resolve_cloth_type(garment_bytes: bytes) -> str:
    """Classify garment type via the GPU inference container, or use env/heuristic fallback."""
    if settings.VTON_PROVIDER in ("catvton_local", "fashn_local"):
        base_url = (
            settings.FASHN_LOCAL_URL
            if settings.VTON_PROVIDER == "fashn_local"
            else settings.CATVTON_LOCAL_URL
        )
        try:
            return _classify_via_server(base_url, garment_bytes)
        except Exception as exc:
            heuristic = _heuristic_cloth_type(garment_bytes)
            logger.warning(
                "Classify via %s failed (%s); using heuristic=%s",
                base_url,
                exc,
                heuristic,
            )
            return heuristic
    return _normalize(settings.CATVTON_CLOTH_TYPE)

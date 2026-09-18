"""Pure helpers for deterministic SKU composition: normalization and hashing."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata

SKU_MAX_LENGTH = 200

_WHITESPACE = re.compile(r"\s+")


class InvalidSkuError(Exception):
    """Raised when an SKU is empty or contains only unsupported characters."""


class UnsupportedFontError(Exception):
    """Raised when a composition requests a font family we cannot render."""


def _is_control(char: str) -> bool:
    return unicodedata.category(char) == "Cc"


def normalize_sku(raw: str) -> str:
    """Returns the canonical SKU text used for both rendering and storage.

    Control characters are dropped (never silently kept in storage while
    invisible in the image), whitespace runs collapse to a single space, and
    the result is NFC-normalized so equivalent inputs hash identically
    (ADR-054).
    """
    if raw is None:
        raise InvalidSkuError("SKU is required")

    without_controls = "".join(char for char in raw if not _is_control(char))
    collapsed = _WHITESPACE.sub(" ", without_controls).strip()
    normalized = unicodedata.normalize("NFC", collapsed)

    if not normalized:
        raise InvalidSkuError("SKU must contain at least one visible character")
    if len(normalized) > SKU_MAX_LENGTH:
        raise InvalidSkuError(f"SKU exceeds {SKU_MAX_LENGTH} characters")
    return normalized


def compute_spec_hash(
    sku: str,
    placement: dict,
    style: dict,
    base_image_key: str,
    font_version: str,
) -> str:
    """Deterministic hash over everything that can change rendered pixels."""
    payload = json.dumps(
        {
            "sku": sku,
            "placement": placement,
            "style": style,
            "base_image_key": base_image_key,
            "font_version": font_version,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

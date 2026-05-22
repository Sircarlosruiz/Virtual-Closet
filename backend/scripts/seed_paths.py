"""Rutas a imágenes de ejemplo para scripts de seed."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def seed_imgs_dir() -> Path:
    """Directorio con modelo.jpeg y producto_1.jpeg."""
    override = os.environ.get("SEED_IMGS_DIR")
    if override:
        return Path(override)
    return REPO_ROOT / "docs" / "imgs"


def seed_image(name: str) -> Path | None:
    path = seed_imgs_dir() / name
    return path if path.is_file() else None

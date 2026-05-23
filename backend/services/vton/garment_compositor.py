"""Dev compositor: cut garment background and blend onto a model photo."""

from __future__ import annotations

import io
import logging

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def composite_garment_on_model(garment_bytes: bytes, model_bytes: bytes) -> bytes:
    """Place a flat-lay / hanger garment onto a full-body model photo."""
    model_rgb = Image.open(io.BytesIO(model_bytes)).convert("RGB")
    garment_rgba = _prepare_garment(garment_bytes)

    model_w, model_h = model_rgb.size
    garment_rgba = _fit_garment_to_model(garment_rgba, model_w, model_h)
    left, top = _placement_offset(garment_rgba, model_w, model_h)

    result = _seamless_blend(model_rgb, garment_rgba, left, top)
    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _prepare_garment(garment_bytes: bytes) -> Image.Image:
    garment = Image.open(io.BytesIO(garment_bytes)).convert("RGBA")
    garment = _remove_background(garment)
    return _crop_to_content(garment)


def _remove_background(image: Image.Image) -> Image.Image:
    try:
        from rembg import remove

        logger.info("Removing garment background with rembg")
        return remove(image)
    except Exception as exc:
        logger.warning("rembg unavailable (%s); using light-background fallback", exc)
        return _remove_light_background(image)


def _remove_light_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if r > 225 and g > 225 and b > 225:
                pixels[x, y] = (r, g, b, 0)
            elif max(r, g, b) - min(r, g, b) < 18 and min(r, g, b) > 190:
                pixels[x, y] = (r, g, b, 0)
    return rgba


def _crop_to_content(image: Image.Image) -> Image.Image:
    alpha = np.array(image.split()[-1])
    coords = np.argwhere(alpha > 16)
    if coords.size == 0:
        return image
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1
    return image.crop((x0, y0, x1, y1))


def _garment_kind(garment: Image.Image) -> str:
    width, height = garment.size
    ratio = height / max(width, 1)
    if ratio >= 1.25:
        return "dress"
    if ratio >= 0.95:
        return "top"
    return "top"


def _fit_garment_to_model(garment: Image.Image, model_w: int, model_h: int) -> Image.Image:
    kind = _garment_kind(garment)
    if kind == "dress":
        target_h = int(model_h * 0.58)
        target_w = int(model_w * 0.52)
    else:
        target_h = int(model_h * 0.34)
        target_w = int(model_w * 0.46)

    src_w, src_h = garment.size
    scale = min(target_w / src_w, target_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    return garment.resize((new_w, new_h), Image.Resampling.LANCZOS)


def _placement_offset(garment: Image.Image, model_w: int, model_h: int) -> tuple[int, int]:
    kind = _garment_kind(garment)
    gw, gh = garment.size
    left = (model_w - gw) // 2

    if kind == "dress":
        top = int(model_h * 0.16)
    else:
        top = int(model_h * 0.14)

    top = min(top, model_h - gh - 1)
    top = max(top, 0)
    return left, top


def _seamless_blend(
    model_rgb: Image.Image, garment_rgba: Image.Image, left: int, top: int
) -> Image.Image:
    model_bgr = cv2.cvtColor(np.array(model_rgb), cv2.COLOR_RGB2BGR)
    garment_np = np.array(garment_rgba)
    garment_bgr = cv2.cvtColor(garment_np, cv2.COLOR_RGBA2BGR)
    mask = garment_np[:, :, 3]

    if mask.max() < 16:
        return _alpha_paste(model_rgb, garment_rgba, left, top)

    gh, gw = garment_bgr.shape[:2]
    model_h, model_w = model_bgr.shape[:2]
    if gw < 8 or gh < 8 or left + gw > model_w or top + gh > model_h:
        return _alpha_paste(model_rgb, garment_rgba, left, top)

    center = (left + gw // 2, top + gh // 2)
    try:
        blended = cv2.seamlessClone(
            garment_bgr,
            model_bgr,
            mask,
            center,
            cv2.NORMAL_CLONE,
        )
        return Image.fromarray(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB))
    except cv2.error as exc:
        logger.warning("seamlessClone failed (%s); using alpha paste", exc)
        return _alpha_paste(model_rgb, garment_rgba, left, top)


def _alpha_paste(
    model_rgb: Image.Image, garment_rgba: Image.Image, left: int, top: int
) -> Image.Image:
    canvas = model_rgb.convert("RGBA")
    canvas.alpha_composite(garment_rgba, (left, top))
    return canvas.convert("RGB")

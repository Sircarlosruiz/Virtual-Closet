"""Post-processing for FASHN try-on outputs.

1. Preserve hands/arms from the original photo (occlusion at dress hem).
2. For one-pieces: full leg artifact repair only when the model wears long pants;
   otherwise keep FASHN legs and optionally restore feet/sandals only.
"""

from __future__ import annotations

import logging
import os

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_parser = None

# Lower-body pants coverage above this → run dark-leg artifact repair.
_PANTS_AREA_RATIO = 0.025


def _get_parser():
    global _parser
    if _parser is None:
        from fashn_human_parser import FashnHumanParser

        _parser = FashnHumanParser(device="cpu")
    return _parser


def _label_ids() -> dict[str, int]:
    from fashn_vton.preprocessing import FASHN_LABELS_TO_IDS

    return FASHN_LABELS_TO_IDS


def _align(
    original: Image.Image, generated: Image.Image
) -> tuple[np.ndarray, np.ndarray]:
    if original.size != generated.size:
        original = original.resize(generated.size, Image.LANCZOS)
    return (
        np.array(original.convert("RGB")),
        np.array(generated.convert("RGB")),
    )


def _blend_original_mask(
    orig: np.ndarray,
    gen: np.ndarray,
    mask: np.ndarray,
    blur_kernel: int = 21,
) -> np.ndarray:
    """Alpha-blend original over generated using a soft mask."""
    alpha = mask.astype(np.float32)
    if alpha.max() > 1.0:
        alpha = alpha / 255.0
    if blur_kernel > 0:
        alpha = cv2.GaussianBlur(alpha, (blur_kernel, blur_kernel), 0)
    alpha = np.clip(alpha, 0.0, 1.0)[:, :, None]
    blended = orig.astype(np.float32) * alpha + gen.astype(np.float32) * (1.0 - alpha)
    return np.clip(blended, 0, 255).astype(np.uint8)


def _skin_like_mask(image: np.ndarray, seg: np.ndarray) -> np.ndarray:
    """Pixels that look like exposed skin (excludes garment bleed into limb regions)."""
    ids = _label_ids()
    skin_labels = [ids["face"], ids["arms"], ids["torso"], ids["hands"]]
    skin_color = _sample_skin_color(image, seg)
    diff = np.linalg.norm(image.astype(np.float32) - skin_color, axis=2)
    lum = image.mean(axis=2)
    skin_like = (diff < 38) & (lum > 55)
    parser_skin = np.isin(seg, skin_labels)
    return (skin_like & parser_skin).astype(np.uint8) * 255


def _limb_mask_from_original(orig: np.ndarray) -> np.ndarray:
    """Mask for hands/fingers only — skin-gated, excluding garment pixels."""
    ids = _label_ids()
    seg = _get_parser().predict(orig)
    hands = (seg == ids["hands"]).astype(np.uint8) * 255
    garment = np.isin(seg, [ids["dress"], ids["skirt"], ids["pants"], ids["top"]])
    skin = _skin_like_mask(orig, seg)
    preserve = cv2.bitwise_and(hands, skin)
    preserve[garment] = 0
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    preserve = cv2.erode(preserve, kernel, iterations=1)
    preserve = cv2.dilate(preserve, kernel, iterations=1)
    return preserve


def preserve_hands_and_arms(original: Image.Image, generated: Image.Image) -> Image.Image:
    """Restore sharp hands/fingers from the original over the try-on result."""
    orig, gen = _align(original, generated)
    mask = _limb_mask_from_original(orig)
    if mask.max() == 0:
        logger.debug("No hands/arms detected; skipping limb preservation")
        return generated
    out = _blend_original_mask(orig, gen, mask, blur_kernel=15)
    return Image.fromarray(out)


def _original_wearing_long_pants(orig: np.ndarray) -> bool:
    """True when the parser sees substantial pants in the lower body."""
    ids = _label_ids()
    seg = _get_parser().predict(orig)
    h = orig.shape[0]
    lower = seg[int(h * 0.42) :, int(orig.shape[1] * 0.15) : int(orig.shape[1] * 0.85)]
    if lower.size == 0:
        return False
    pants_ratio = (lower == ids["pants"]).sum() / lower.size
    logger.info("Original lower-body pants ratio=%.3f", pants_ratio)
    return pants_ratio >= _PANTS_AREA_RATIO


def _estimate_garment_hem(seg: np.ndarray, width: int) -> int | None:
    ids = _label_ids()
    garment_ids = [ids["dress"], ids["skirt"]]
    x0, x1 = int(width * 0.22), int(width * 0.78)
    center = seg[:, x0:x1]
    rows = np.where(np.isin(center, garment_ids).any(axis=1))[0]
    if rows.size == 0:
        return None
    return int(rows.max())


def _sample_skin_color(image: np.ndarray, seg: np.ndarray) -> np.ndarray:
    """Sample skin from face/arms/torso/hands only — never from generated legs."""
    ids = _label_ids()
    skin_labels = [ids["face"], ids["arms"], ids["torso"], ids["hands"]]
    mask = np.isin(seg, skin_labels)
    pixels = image[mask]
    if pixels.size == 0:
        h, w = image.shape[:2]
        pixels = image[int(h * 0.15) : int(h * 0.35), int(w * 0.35) : int(w * 0.65)].reshape(
            -1, 3
        )
    lum = pixels.mean(axis=1)
    pixels = pixels[lum > 80]
    if pixels.size == 0:
        return image[int(image.shape[0] * 0.2), int(image.shape[1] * 0.5)].astype(np.float32)
    return pixels.mean(axis=0).astype(np.float32)


def _feet_mask_from_original(orig: np.ndarray) -> np.ndarray:
    ids = _label_ids()
    seg = _get_parser().predict(orig)
    feet = (seg == ids["feet"]).astype(np.uint8) * 255
    if feet.max() == 0:
        h = orig.shape[0]
        feet[int(h * 0.84) :, :] = 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    feet = cv2.dilate(feet, kernel, iterations=2)
    return feet.astype(np.float32) / 255.0


def restore_feet_only(original: Image.Image, generated: Image.Image) -> Image.Image:
    """Blend original feet/sandals when legs are already bare in the source photo."""
    orig, gen = _align(original, generated)
    feet_mask = _feet_mask_from_original(orig)
    feet_mask = cv2.GaussianBlur(feet_mask, (0, 0), sigmaX=4, sigmaY=4)
    out = _blend_original_mask(orig, gen, feet_mask, blur_kernel=0)
    return Image.fromarray(out)


def fix_one_piece_legs(original: Image.Image, generated: Image.Image) -> Image.Image:
    """Remove dark calf artifacts (pants → dress) and restore feet."""
    orig, gen = _align(original, generated)
    h, w = gen.shape[:2]

    seg = _get_parser().predict(gen)
    hem_y = _estimate_garment_hem(seg, w)
    if hem_y is None:
        logger.debug("No garment hem detected; skipping leg artifact repair")
        return restore_feet_only(original, generated)

    skin = _sample_skin_color(gen, seg)
    repair_top = min(h - 1, hem_y + max(6, int(h * 0.012)))
    out = gen.astype(np.float32)

    for y in range(repair_top, h):
        row = gen[y].astype(np.float32)
        lum = row.mean(axis=1)
        dist = np.linalg.norm(row - skin, axis=1)
        artifact = (lum < 130) & (dist > 28)
        if not artifact.any():
            continue
        t = (y - repair_top) / max(h - repair_top, 1)
        target = skin * (0.90 + 0.10 * min(t * 2.0, 1.0))
        out[y, artifact] = target

    band_end = int(h * 0.88)
    if band_end > repair_top:
        band = out[repair_top:band_end].astype(np.uint8)
        band = cv2.bilateralFilter(band, d=7, sigmaColor=50, sigmaSpace=50)
        out[repair_top:band_end] = band.astype(np.float32)

    feet_mask = _feet_mask_from_original(orig)
    feet_mask = cv2.GaussianBlur(feet_mask, (0, 0), sigmaX=4, sigmaY=4)
    out = _blend_original_mask(
        orig,
        np.clip(out, 0, 255).astype(np.uint8),
        feet_mask,
        blur_kernel=0,
    )
    return Image.fromarray(out)


def postprocess_tryon(
    original: Image.Image,
    generated: Image.Image,
    cloth_type: str,
) -> Image.Image:
    """Apply limb preservation and conditional leg post-processing."""
    result = generated

    if os.environ.get("FASHN_PRESERVE_LIMBS", "true").lower() == "true":
        result = preserve_hands_and_arms(original, result)

    if cloth_type != "overall":
        return result

    if os.environ.get("FASHN_LEG_POSTPROCESS", "true").lower() != "true":
        return result

    orig, _ = _align(original, result)
    if _original_wearing_long_pants(orig):
        logger.info("Long pants detected — running full leg artifact repair")
        result = fix_one_piece_legs(original, result)
    else:
        # FASHN already renders bare legs well; blending original feet/legs
        # reintroduces ghosting, dress colour, and skin-tone blocks.
        logger.info("Bare legs detected — skipping leg postprocess")

    return result

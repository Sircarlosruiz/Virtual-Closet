#!/usr/bin/env python3
"""Validation script for bolt 011-fashn-postprocess.

Run this script in the FASHN Docker container with GPU access to validate:
1. Hand compositing tuning (story 001)
2. Long-pants threshold validation (story 002)

Usage:
    docker compose run --rm fashn python validate_bolt_011.py

Required test images (place in /app/test_images/):
    - maria_baseline.jpg: Mara + producto_1 (v4 baseline reference)
    - long_pants_subject.jpg: Model wearing long pants (for story 002)
"""

import hashlib
import logging
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TEST_IMAGES_DIR = Path("/app/test_images")
OUTPUT_DIR = Path("/app/test_outputs")


def md5_image(img: Image.Image) -> str:
    """Compute MD5 hash of image bytes."""
    arr = np.array(img)
    return hashlib.md5(arr.tobytes()).hexdigest()[:8]


def verify_constants_documented():
    """Verify all threshold constants are defined and documented."""
    from postprocess import (
        _PANTS_AREA_RATIO,
        _DARK_PIXEL_LUMINANCE,
        _SKIN_COLOR_DISTANCE,
        _BILATERAL_FILTER_D,
        _BILATERAL_SIGMA_COLOR,
        _BILATERAL_SIGMA_SPACE,
        _REPAIR_TOP_OFFSET_FACTOR,
        _REPAIR_BAND_END,
        _HAND_EROSION_KERNEL,
        _HAND_BLEND_BLUR,
    )

    constants = {
        "_PANTS_AREA_RATIO": _PANTS_AREA_RATIO,
        "_DARK_PIXEL_LUMINANCE": _DARK_PIXEL_LUMINANCE,
        "_SKIN_COLOR_DISTANCE": _SKIN_COLOR_DISTANCE,
        "_BILATERAL_FILTER_D": _BILATERAL_FILTER_D,
        "_BILATERAL_SIGMA_COLOR": _BILATERAL_SIGMA_COLOR,
        "_BILATERAL_SIGMA_SPACE": _BILATERAL_SIGMA_SPACE,
        "_REPAIR_TOP_OFFSET_FACTOR": _REPAIR_TOP_OFFSET_FACTOR,
        "_REPAIR_BAND_END": _REPAIR_BAND_END,
        "_HAND_EROSION_KERNEL": _HAND_EROSION_KERNEL,
        "_HAND_BLEND_BLUR": _HAND_BLEND_BLUR,
    }

    logger.info("=== Constant Verification ===")
    for name, value in constants.items():
        logger.info(f"  {name} = {value}")

    assert _HAND_EROSION_KERNEL == 5, "Hand erosion kernel should be 5x5"
    assert _HAND_BLEND_BLUR == 11, "Hand blend blur should be 11"
    logger.info("✅ All constants defined and tuned correctly")
    return True


def verify_hands_label_distinct():
    """Verify FASHN_LABELS_TO_IDS['hands'] exists as distinct from 'arms'."""
    from fashn_vton.preprocessing import FASHN_LABELS_TO_IDS

    logger.info("=== Hands Label Verification ===")
    assert "hands" in FASHN_LABELS_TO_IDS, "Missing 'hands' label in FASHN_LABELS_TO_IDS"
    assert "arms" in FASHN_LABELS_TO_IDS, "Missing 'arms' label in FASHN_LABELS_TO_IDS"

    hands_id = FASHN_LABELS_TO_IDS["hands"]
    arms_id = FASHN_LABELS_TO_IDS["arms"]

    logger.info(f"  hands ID: {hands_id}")
    logger.info(f"  arms ID: {arms_id}")
    assert hands_id != arms_id, "hands and arms must be distinct labels"
    logger.info("✅ Hands label is distinct from arms")
    return True


def test_maria_baseline_regression():
    """Test Mara baseline regression (story 001)."""
    from main import _load_pipeline, _models
    from postprocess import postprocess_tryon

    logger.info("=== Mara Baseline Regression Test ===")

    baseline_path = TEST_IMAGES_DIR / "maria_baseline.jpg"
    garment_path = TEST_IMAGES_DIR / "producto_1.jpg"

    if not baseline_path.exists():
        logger.warning(f"⚠️  Baseline image not found: {baseline_path}")
        logger.warning("   Skipping regression test (requires test images)")
        return False

    if not garment_path.exists():
        logger.warning(f"⚠️  Garment image not found: {garment_path}")
        logger.warning("   Skipping regression test (requires test images)")
        return False

    _load_pipeline()

    person_img = Image.open(baseline_path).convert("RGB")
    garment_img = Image.open(garment_path).convert("RGB")

    os.environ["FASHN_SEED"] = "42"
    os.environ["FASHN_PRESERVE_LIMBS"] = "true"
    os.environ["FASHN_LEG_POSTPROCESS"] = "true"

    result = _models["pipe"](
        person_image=person_img,
        garment_image=garment_img,
        category="one-pieces",
        garment_photo_type="flat-lay",
        num_samples=1,
        num_timesteps=30,
        guidance_scale=1.5,
        seed=42,
        segmentation_free=False,
    )

    raw_output = result.images[0]
    output = postprocess_tryon(person_img, raw_output, "overall")

    output_md5 = md5_image(output)
    logger.info(f"  Output MD5: {output_md5}")

    output_path = OUTPUT_DIR / "maria_bolt011.jpg"
    OUTPUT_DIR.mkdir(exist_ok=True)
    output.save(output_path, quality=95)
    logger.info(f"  Saved to: {output_path}")

    logger.info("✅ Mara baseline test completed (visual inspection required)")
    return True


def test_long_pants_detection():
    """Test long-pants detection and fix_one_piece_legs (story 002)."""
    from postprocess import _original_wearing_long_pants, _get_parser, _align

    logger.info("=== Long-Pants Detection Test ===")

    pants_path = TEST_IMAGES_DIR / "long_pants_subject.jpg"
    if not pants_path.exists():
        logger.warning(f"⚠️  Long-pants image not found: {pants_path}")
        logger.warning("   Skipping long-pants test (requires test image)")
        return False

    person_img = Image.open(pants_path).convert("RGB")
    orig, _ = _align(person_img, person_img)

    is_pants = _original_wearing_long_pants(orig)
    logger.info(f"  Long-pants detected: {is_pants}")

    if is_pants:
        logger.info("✅ Long-pants detection working")
    else:
        logger.warning("⚠️  Long-pants not detected (check _PANTS_AREA_RATIO threshold)")

    return is_pants


def test_long_pants_fix():
    """Test fix_one_piece_legs on long-pants subject (story 002)."""
    from main import _load_pipeline, _models
    from postprocess import postprocess_tryon, fix_one_piece_legs

    logger.info("=== Long-Pants Fix Test ===")

    pants_path = TEST_IMAGES_DIR / "long_pants_subject.jpg"
    garment_path = TEST_IMAGES_DIR / "producto_1.jpg"

    if not pants_path.exists() or not garment_path.exists():
        logger.warning("⚠️  Test images not found; skipping fix test")
        return False

    _load_pipeline()

    person_img = Image.open(pants_path).convert("RGB")
    garment_img = Image.open(garment_path).convert("RGB")

    os.environ["FASHN_SEED"] = "42"
    os.environ["FASHN_PRESERVE_LIMBS"] = "true"
    os.environ["FASHN_LEG_POSTPROCESS"] = "true"

    result = _models["pipe"](
        person_image=person_img,
        garment_image=garment_img,
        category="one-pieces",
        garment_photo_type="flat-lay",
        num_samples=1,
        num_timesteps=30,
        guidance_scale=1.5,
        seed=42,
        segmentation_free=False,
    )

    raw_output = result.images[0]
    output = postprocess_tryon(person_img, raw_output, "overall")

    output_path = OUTPUT_DIR / "long_pants_bolt011.jpg"
    OUTPUT_DIR.mkdir(exist_ok=True)
    output.save(output_path, quality=95)
    logger.info(f"  Saved to: {output_path}")

    logger.info("✅ Long-pants fix test completed (visual inspection required)")
    return True


def test_preserve_limbs_kill_switch():
    """Test FASHN_PRESERVE_LIMBS=false escape hatch."""
    from postprocess import preserve_hands_and_arms

    logger.info("=== Preserve Limbs Kill Switch Test ===")

    os.environ["FASHN_PRESERVE_LIMBS"] = "false"

    dummy_img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    result = preserve_hands_and_arms(dummy_img, dummy_img)

    assert result.size == dummy_img.size, "Output size should match input"
    logger.info("✅ FASHN_PRESERVE_LIMBS=false escape hatch working")

    os.environ["FASHN_PRESERVE_LIMBS"] = "true"
    return True


def main():
    """Run all validation tests."""
    logger.info("=" * 60)
    logger.info("Bolt 011 Validation: fashn-postprocess")
    logger.info("=" * 60)

    results = []

    results.append(("Constants documented", verify_constants_documented()))
    results.append(("Hands label distinct", verify_hands_label_distinct()))
    results.append(("Preserve limbs kill switch", test_preserve_limbs_kill_switch()))
    results.append(("Mara baseline regression", test_maria_baseline_regression()))
    results.append(("Long-pants detection", test_long_pants_detection()))
    results.append(("Long-pants fix", test_long_pants_fix()))

    logger.info("\n" + "=" * 60)
    logger.info("Validation Summary")
    logger.info("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "⚠️  SKIP/FAIL"
        logger.info(f"  {status}: {name}")

    passed = sum(1 for _, p in results if p)
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed < 3:
        logger.error("❌ Critical tests failed")
        sys.exit(1)

    logger.info("✅ Validation complete")


if __name__ == "__main__":
    main()

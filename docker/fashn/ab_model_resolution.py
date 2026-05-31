#!/usr/bin/env python3
"""A/B test: model image resolution (thumbnail vs full-res).

Compares thumbnail (~400×600) vs full-resolution model input on VTON output quality.
Uses identical seed to isolate the variable being tested.

Usage:
    docker compose run --rm fashn python ab_model_resolution.py

Required test images (place in /app/test_images/):
    - maria_fullres.jpg (full-resolution model photo)
    - maria_thumbnail.jpg (thumbnail version ~400×600)
    - garment.jpg (garment image for testing)

Output:
    /app/test_outputs/ab_resolution/
        maria_thumbnail_input.jpg
        maria_fullres_input.jpg
"""

import hashlib
import io
import logging
import os
import time
from pathlib import Path

import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TEST_IMAGES_DIR = Path("/app/test_images")
OUTPUT_DIR = Path("/app/test_outputs/ab_resolution")


def md5_image(img: Image.Image) -> str:
    """Compute MD5 hash of image bytes."""
    arr = np.array(img)
    return hashlib.md5(arr.tobytes()).hexdigest()[:8]


def run_ab_test():
    """Run model resolution A/B test."""
    from main import _load_pipeline, _models
    from postprocess import postprocess_tryon

    fullres_path = TEST_IMAGES_DIR / "maria_fullres.jpg"
    thumbnail_path = TEST_IMAGES_DIR / "maria_thumbnail.jpg"
    garment_path = TEST_IMAGES_DIR / "garment.jpg"

    if not all(p.exists() for p in [fullres_path, thumbnail_path, garment_path]):
        logger.error("Missing test images:")
        logger.error(f"  {fullres_path}: {fullres_path.exists()}")
        logger.error(f"  {thumbnail_path}: {thumbnail_path.exists()}")
        logger.error(f"  {garment_path}: {garment_path.exists()}")
        return False

    logger.info(f"=== Model Resolution A/B Test ===")

    _load_pipeline()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    os.environ["FASHN_SEED"] = "42"
    os.environ["FASHN_PRESERVE_LIMBS"] = "true"
    os.environ["FASHN_LEG_POSTPROCESS"] = "true"

    garment_img = Image.open(garment_path).convert("RGB")

    results = []

    for label, model_path in [("thumbnail", thumbnail_path), ("fullres", fullres_path)]:
        logger.info(f"\n--- {label} ---")

        person_img = Image.open(model_path).convert("RGB")
        logger.info(f"  Input size: {person_img.size}")

        start_time = time.time()

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

        inference_time = time.time() - start_time

        raw_output = result.images[0]
        output = postprocess_tryon(person_img, raw_output, "overall")

        output_md5 = md5_image(output)
        buf = io.BytesIO()
        output.save(buf, format="JPEG", quality=95)
        output_bytes = buf.getvalue()

        output_path = OUTPUT_DIR / f"maria_{label}_input.jpg"
        output.save(output_path, quality=95)

        logger.info(f"  Output MD5: {output_md5}")
        logger.info(f"  Output size: {output.size}")
        logger.info(f"  Output bytes: {len(output_bytes)}")
        logger.info(f"  Inference time: {inference_time:.2f}s")
        logger.info(f"  Saved: {output_path}")

        results.append({
            "label": label,
            "input_size": person_img.size,
            "output_size": output.size,
            "md5": output_md5,
            "bytes": len(output_bytes),
            "inference_time": inference_time,
            "path": str(output_path),
        })

    logger.info("\n=== A/B Test Complete ===")
    logger.info("Visual comparison required:")
    for r in results:
        logger.info(f"  {r['label']}: {r['path']}")
        logger.info(f"    Input: {r['input_size']}, Output: {r['output_size']}")
        logger.info(f"    Time: {r['inference_time']:.2f}s, Bytes: {r['bytes']}")

    return True


def main():
    """Run A/B test."""
    logger.info("=" * 60)
    logger.info("A/B Test: Model Resolution (thumbnail vs full-res)")
    logger.info("=" * 60)

    success = run_ab_test()

    if success:
        logger.info("\n✅ A/B test completed successfully")
        logger.info("\nNext steps:")
        logger.info("1. Visually compare outputs: hand boundary, leg texture, detail")
        logger.info("2. If full-res shows meaningful improvement:")
        logger.info("   - Add image_key field to ModeloIA model")
        logger.info("   - Update upload flow to store both thumbnail and full-res")
        logger.info("   - Update generate_vton.py to use image_key")
        logger.info("3. If no meaningful difference:")
        logger.info("   - Document decision to keep thumbnail path")
    else:
        logger.error("\n❌ A/B test failed")


if __name__ == "__main__":
    main()

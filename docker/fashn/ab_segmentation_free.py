#!/usr/bin/env python3
"""A/B test: segmentation_free flag for one-piece garments.

Compares segmentation_free=True vs False on ≥2 subjects with cloth_type=overall.
Uses identical seed to isolate the variable being tested.

Usage:
    docker compose run --rm fashn python ab_segmentation_free.py

Required test images (place in /app/test_images/):
    - subject_1_garment.jpg, subject_1_model.jpg (first subject)
    - subject_2_garment.jpg, subject_2_model.jpg (second subject)
    - (optional) subject_3_*, subject_4_* for additional subjects

Output:
    /app/test_outputs/ab_segfree/
        subject_1_segfree_true.jpg
        subject_1_segfree_false.jpg
        subject_2_segfree_true.jpg
        subject_2_segfree_false.jpg
        ...
"""

import hashlib
import io
import logging
import os
from pathlib import Path

import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TEST_IMAGES_DIR = Path("/app/test_images")
OUTPUT_DIR = Path("/app/test_outputs/ab_segfree")


def md5_image(img: Image.Image) -> str:
    """Compute MD5 hash of image bytes."""
    arr = np.array(img)
    return hashlib.md5(arr.tobytes()).hexdigest()[:8]


def discover_subjects() -> list[str]:
    """Find all subjects with both garment and model images."""
    subjects = []
    for i in range(1, 10):
        garment = TEST_IMAGES_DIR / f"subject_{i}_garment.jpg"
        model = TEST_IMAGES_DIR / f"subject_{i}_model.jpg"
        if garment.exists() and model.exists():
            subjects.append(f"subject_{i}")
    return subjects


def run_ab_test():
    """Run segmentation_free A/B test on all discovered subjects."""
    from main import _load_pipeline, _models
    from postprocess import postprocess_tryon

    subjects = discover_subjects()
    if len(subjects) < 2:
        logger.error(f"Need ≥2 subjects, found {len(subjects)}")
        logger.error("Place subject_N_garment.jpg and subject_N_model.jpg in /app/test_images/")
        return False

    logger.info(f"=== segmentation_free A/B Test ===")
    logger.info(f"Subjects: {subjects}")

    _load_pipeline()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    os.environ["FASHN_SEED"] = "42"
    os.environ["FASHN_PRESERVE_LIMBS"] = "true"
    os.environ["FASHN_LEG_POSTPROCESS"] = "true"

    results = []

    for subject in subjects:
        logger.info(f"\n--- {subject} ---")

        garment_path = TEST_IMAGES_DIR / f"{subject}_garment.jpg"
        model_path = TEST_IMAGES_DIR / f"{subject}_model.jpg"

        garment_img = Image.open(garment_path).convert("RGB")
        person_img = Image.open(model_path).convert("RGB")

        for seg_free in [False, True]:
            label = "true" if seg_free else "false"
            logger.info(f"  Running segmentation_free={label}")

            result = _models["pipe"](
                person_image=person_img,
                garment_image=garment_img,
                category="one-pieces",
                garment_photo_type="flat-lay",
                num_samples=1,
                num_timesteps=30,
                guidance_scale=1.5,
                seed=42,
                segmentation_free=seg_free,
            )

            raw_output = result.images[0]
            output = postprocess_tryon(person_img, raw_output, "overall")

            output_md5 = md5_image(output)
            buf = io.BytesIO()
            output.save(buf, format="JPEG", quality=95)
            output_bytes = buf.getvalue()

            output_path = OUTPUT_DIR / f"{subject}_segfree_{label}.jpg"
            output.save(output_path, quality=95)

            logger.info(f"    MD5: {output_md5}")
            logger.info(f"    Size: {len(output_bytes)} bytes")
            logger.info(f"    Saved: {output_path}")

            results.append({
                "subject": subject,
                "seg_free": seg_free,
                "md5": output_md5,
                "bytes": len(output_bytes),
                "path": str(output_path),
            })

    logger.info("\n=== A/B Test Complete ===")
    logger.info("Visual comparison required:")
    for r in results:
        logger.info(f"  {r['subject']} seg_free={r['seg_free']}: {r['path']}")

    return True


def main():
    """Run A/B test."""
    logger.info("=" * 60)
    logger.info("A/B Test: segmentation_free for one-pieces")
    logger.info("=" * 60)

    success = run_ab_test()

    if success:
        logger.info("\n✅ A/B test completed successfully")
        logger.info("\nNext steps:")
        logger.info("1. Visually compare outputs for each subject")
        logger.info("2. Evaluate: dress silhouette, leg boundary, hand region")
        logger.info("3. Document preferred value with rationale")
        logger.info("4. Update _segmentation_free_for() inline comment")
        logger.info("5. Update docker-compose.yml / .env.example")
    else:
        logger.error("\n❌ A/B test failed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Integration test for TryOff FLUX garment extraction container.

Runs POST /tryoff against a running container and validates output.

Usage:
    # From host (container must be running)
    make tryoff-test

    # Or directly
    python docker/flux/run_test.py --image docs/imgs/test-tryoff.jpg --garment-type upper

    # Inside container
    python run_test.py --image /app/test-subjects/person.jpg --garment-type upper
"""

import argparse
import hashlib
import io
import logging
import sys
import time
from pathlib import Path

import requests
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

TRYOFF_URL = "http://localhost:8003"
MIN_OUTPUT_WIDTH = 768
MIN_OUTPUT_HEIGHT = 1024
MAX_INFERENCE_SECONDS = 120


def check_health() -> bool:
    """Check if TryOff container is healthy and model is loaded."""
    try:
        response = requests.get(f"{TRYOFF_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error(f"Health check returned {response.status_code}")
            return False
        data = response.json()
        if not data.get("model_loaded"):
            logger.error("Model not loaded yet")
            return False
        logger.info(f"Health OK: device={data.get('device')}")
        return True
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


def run_tryoff(image_path: Path, garment_type: str) -> tuple[bytes, float]:
    """Call POST /tryoff and return (output_bytes, elapsed_seconds)."""
    url = f"{TRYOFF_URL}/tryoff"

    with open(image_path, "rb") as f:
        files = {"image": (image_path.name, f, "image/jpeg")}
        data = {"garment_type": garment_type}

        t0 = time.monotonic()
        response = requests.post(url, files=files, data=data, timeout=MAX_INFERENCE_SECONDS)
        elapsed = time.monotonic() - t0

    response.raise_for_status()
    return response.content, elapsed


def validate_output(output_bytes: bytes) -> dict:
    """Validate output PNG meets acceptance criteria."""
    results = {
        "format": "unknown",
        "width": 0,
        "height": 0,
        "dimensions_ok": False,
        "has_content": False,
    }

    try:
        img = Image.open(io.BytesIO(output_bytes))
        results["format"] = img.format
        results["width"] = img.width
        results["height"] = img.height
        results["dimensions_ok"] = img.width >= MIN_OUTPUT_WIDTH and img.height >= MIN_OUTPUT_HEIGHT
        results["has_content"] = len(output_bytes) > 1000
    except Exception as e:
        results["error"] = str(e)

    return results


def test_health_endpoint():
    """Test GET /health returns correct status."""
    logger.info("--- Test: GET /health ---")
    response = requests.get(f"{TRYOFF_URL}/health", timeout=5)
    data = response.json()

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert data["status"] == "ok", f"Expected status=ok, got {data['status']}"
    assert data["model_loaded"] is True, f"Expected model_loaded=True"
    assert data["device"] == "cuda", f"Expected device=cuda, got {data['device']}"
    logger.info("  PASS: health endpoint returns correct status")


def test_invalid_garment_type():
    """Test POST /tryoff with invalid garment_type returns 422."""
    logger.info("--- Test: invalid garment_type ---")
    dummy = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    files = {"image": ("test.png", dummy, "image/png")}
    data = {"garment_type": "invalid"}

    response = requests.post(f"{TRYOFF_URL}/tryoff", files=files, data=data)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    logger.info("  PASS: invalid garment_type returns 422")


def test_unsupported_format():
    """Test POST /tryoff with BMP returns 400."""
    logger.info("--- Test: unsupported image format ---")
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    buf.seek(0)

    files = {"image": ("test.bmp", buf, "image/bmp")}
    data = {"garment_type": "upper"}

    response = requests.post(f"{TRYOFF_URL}/tryoff", files=files, data=data)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    logger.info("  PASS: BMP format returns 400")


def test_oversized_image():
    """Test POST /tryoff with >10MB image returns 413."""
    logger.info("--- Test: oversized image ---")
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024 * 1024)
    files = {"image": ("huge.png", io.BytesIO(oversized), "image/png")}
    data = {"garment_type": "upper"}

    response = requests.post(f"{TRYOFF_URL}/tryoff", files=files, data=data)
    assert response.status_code == 413, f"Expected 413, got {response.status_code}"
    logger.info("  PASS: oversized image returns 413")


def test_inference(image_path: Path, garment_type: str):
    """Test POST /tryoff with valid input returns correct output."""
    logger.info(f"--- Test: inference ({garment_type}) ---")

    output_bytes, elapsed = run_tryoff(image_path, garment_type)
    output_md5 = hashlib.md5(output_bytes).hexdigest()[:8]

    logger.info(f"  Inference time: {elapsed:.1f}s")
    logger.info(f"  Output MD5: {output_md5}")
    logger.info(f"  Output size: {len(output_bytes)} bytes")

    validation = validate_output(output_bytes)
    logger.info(f"  Format: {validation['format']}")
    logger.info(f"  Dimensions: {validation['width']}x{validation['height']}")

    assert validation["format"] == "PNG", f"Expected PNG, got {validation['format']}"
    assert validation["dimensions_ok"], f"Dimensions {validation['width']}x{validation['height']} below minimum {MIN_OUTPUT_WIDTH}x{MIN_OUTPUT_HEIGHT}"
    assert validation["has_content"], "Output image appears empty"
    assert elapsed < MAX_INFERENCE_SECONDS, f"Inference took {elapsed:.1f}s (max {MAX_INFERENCE_SECONDS}s)"

    logger.info("  PASS: inference returns valid PNG within time limit")


def main():
    parser = argparse.ArgumentParser(description="TryOff integration test")
    parser.add_argument("--image", type=Path, help="Source image path")
    parser.add_argument("--garment-type", default="upper", choices=["upper", "lower", "dress"])
    parser.add_argument("--skip-inference", action="store_true", help="Skip GPU inference test")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("TryOff FLUX — Integration Test Suite")
    logger.info("=" * 60)

    if not check_health():
        logger.error("Container not healthy. Run: make tryoff-restart")
        sys.exit(1)

    passed = 0
    failed = 0

    for test_fn in [test_health_endpoint, test_invalid_garment_type, test_unsupported_format, test_oversized_image]:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            logger.error(f"  FAIL: {e}")
            failed += 1

    if not args.skip_inference:
        if args.image and args.image.exists():
            try:
                test_inference(args.image, args.garment_type)
                passed += 1
            except Exception as e:
                logger.error(f"  FAIL: {e}")
                failed += 1
        else:
            logger.warning("Skipping inference test (no --image provided)")

    logger.info("\n" + "=" * 60)
    logger.info(f"Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

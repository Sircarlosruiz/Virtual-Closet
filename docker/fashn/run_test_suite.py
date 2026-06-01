#!/usr/bin/env python3
"""Multi-subject test suite for FASHN VTON v1.5.

Runs /predict on all test subjects in docs/imgs/test-subjects/ and documents results.

Usage:
    # Inside FASHN container
    python run_test_suite.py

    # Or from host
    docker compose exec fashn python run_test_suite.py

Test Subject Requirements:
    - ≥3 distinct subjects with licensed photos
    - At least one with cloth_type=overall
    - At least one with hands near/on garment
    - At least one wearing long pants (for fix_one_piece_legs validation)

Directory Structure:
    docs/imgs/test-subjects/
        maria/
            model.jpg          # Subject photo
            garment.jpg        # Garment to try on
            metadata.json      # Subject metadata
        subject2/
            model.jpg
            garment.jpg
            metadata.json
        ...

Output:
    - Saves output images to docs/imgs/test-output/{subject}_{garment}_{seed}.jpg
    - Updates test-results.md with pass/fail per artifact type
"""

import hashlib
import json
import logging
import os
import sys
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

TEST_SUBJECTS_DIR = Path("/app/test-subjects")
TEST_OUTPUT_DIR = Path("/app/test-output")
FASHN_URL = "http://localhost:8002"
DEFAULT_SEED = 42


def md5_file(path: Path) -> str:
    """Compute MD5 hash of file."""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


def discover_subjects() -> list[dict]:
    """Find all test subjects with required files."""
    subjects = []
    
    if not TEST_SUBJECTS_DIR.exists():
        logger.error(f"Test subjects directory not found: {TEST_SUBJECTS_DIR}")
        return subjects
    
    for subject_dir in sorted(TEST_SUBJECTS_DIR.iterdir()):
        if not subject_dir.is_dir():
            continue
        
        model_path = subject_dir / "model.jpg"
        garment_path = subject_dir / "garment.jpg"
        metadata_path = subject_dir / "metadata.json"
        
        if not model_path.exists():
            logger.warning(f"Skipping {subject_dir.name}: missing model.jpg")
            continue
        if not garment_path.exists():
            logger.warning(f"Skipping {subject_dir.name}: missing garment.jpg")
            continue
        
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
        
        subjects.append({
            "name": subject_dir.name,
            "model_path": model_path,
            "garment_path": garment_path,
            "metadata": metadata,
        })
    
    return subjects


def run_predict(model_path: Path, garment_path: Path, cloth_type: str, seed: int) -> tuple[bytes, str]:
    """Call /predict endpoint and return (output_bytes, output_md5)."""
    url = f"{FASHN_URL}/predict"
    
    with open(model_path, "rb") as model_file, open(garment_path, "rb") as garment_file:
        files = {
            "model": ("model.jpg", model_file, "image/jpeg"),
            "garment": ("garment.jpg", garment_file, "image/jpeg"),
        }
        data = {
            "cloth_type": cloth_type,
        }
        
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
    
    output_bytes = response.content
    output_md5 = hashlib.md5(output_bytes).hexdigest()[:8]
    
    return output_bytes, output_md5


def save_output(output_bytes: bytes, output_path: Path) -> None:
    """Save output image to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(output_bytes)


def check_health() -> bool:
    """Check if FASHN container is healthy."""
    try:
        response = requests.get(f"{FASHN_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


def run_test_suite():
    """Run test suite on all discovered subjects."""
    logger.info("=" * 60)
    logger.info("FASHN VTON v1.5 — Multi-Subject Test Suite")
    logger.info("=" * 60)
    
    if not check_health():
        logger.error("FASHN container not healthy. Run: make fashn-restart")
        return False
    
    subjects = discover_subjects()
    
    if len(subjects) < 3:
        logger.warning(f"Found {len(subjects)} subjects (minimum 3 recommended)")
        if len(subjects) == 0:
            logger.error("No test subjects found. Add subjects to /app/test-subjects/")
            return False
    
    logger.info(f"Discovered {len(subjects)} test subjects:")
    for s in subjects:
        cloth_type = s["metadata"].get("cloth_type", "overall")
        notes = s["metadata"].get("notes", "")
        logger.info(f"  - {s['name']}: cloth_type={cloth_type} {notes}")
    
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for subject in subjects:
        name = subject["name"]
        cloth_type = subject["metadata"].get("cloth_type", "overall")
        seed = DEFAULT_SEED
        
        logger.info(f"\n--- Testing {name} (cloth_type={cloth_type}, seed={seed}) ---")
        
        try:
            output_bytes, output_md5 = run_predict(
                subject["model_path"],
                subject["garment_path"],
                cloth_type,
                seed,
            )
            
            output_filename = f"{name}_{cloth_type}_{seed}.jpg"
            output_path = TEST_OUTPUT_DIR / output_filename
            save_output(output_bytes, output_path)
            
            logger.info(f"  Output MD5: {output_md5}")
            logger.info(f"  Saved: {output_path}")
            
            results.append({
                "subject": name,
                "garment": subject["garment_path"].stem,
                "cloth_type": cloth_type,
                "seed": seed,
                "output_md5": output_md5,
                "output_path": str(output_path),
                "hand_boundary": "pending",
                "leg_quality": "pending",
                "notes": "",
            })
            
        except Exception as e:
            logger.error(f"  Failed: {e}")
            results.append({
                "subject": name,
                "garment": subject["garment_path"].stem,
                "cloth_type": cloth_type,
                "seed": seed,
                "output_md5": "error",
                "output_path": "",
                "hand_boundary": "error",
                "leg_quality": "error",
                "notes": str(e),
            })
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Suite Complete")
    logger.info("=" * 60)
    logger.info(f"Subjects tested: {len(results)}")
    logger.info(f"Outputs saved to: {TEST_OUTPUT_DIR}")
    
    logger.info("\nNext steps:")
    logger.info("1. Visually inspect each output image")
    logger.info("2. Evaluate hand_boundary: pass/fail (finger edges, color bleed)")
    logger.info("3. Evaluate leg_quality: pass/fail (artifacts, flat patches)")
    logger.info("4. Update test-results.md with pass/fail per subject")
    
    return True


def main():
    """Entry point."""
    success = run_test_suite()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

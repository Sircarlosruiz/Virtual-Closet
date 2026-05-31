---
stage: plan
bolt: 012-fashn-postprocess
created: 2026-05-31T12:00:00Z
---

## Implementation Plan: fashn-postprocess (A/B Evaluations)

### Objective

Run controlled A/B evaluations to determine optimal FASHN configuration for one-piece garments: (1) `segmentation_free` flag impact, and (2) model image resolution (thumbnail vs full-res). Document results and implement winning defaults.

### Deliverables

1 - **A/B test script for segmentation_free** — Automated script that runs both arms on ≥2 subjects with identical seed, saves labeled outputs for comparison
2 - **A/B test script for model resolution** — Automated script comparing thumbnail (~400×600) vs full-res model input, saves labeled outputs
3 - **Updated `_segmentation_free_for()` in `main.py`** — Inline comment documenting A/B outcome and rationale
4 - **Updated `docker-compose.yml` / `.env.example`** — Reflect chosen `FASHN_SEGMENTATION_FREE` default
5 - **Updated Celery worker** (if full-res wins) — `generate_vton.py` updated to use `modelo.image_key` instead of `modelo.thumbnail_key`
6 - **A/B results documentation** — Documented comparison with visual evidence and decision rationale

### Dependencies

- **011-fashn-postprocess** (✅ complete): Stable code baseline with tuned hand compositing and documented constants
- **FASHN Docker container with GPU**: Required to run A/B inference
- **≥2 test subjects with one-piece garments**: Required for segmentation_free A/B
- **Model images at both thumbnail and full-res**: Required for resolution A/B
- **`ModeloIA.image_key`**: Need to verify this field exists on the model (currently only `thumbnail_key` is confirmed in the schema)

### Technical Approach

**Story 003 — segmentation_free A/B Test**:

1. Create `docker/fashn/ab_segmentation_free.py` — Script that:
   - Loads test subject images (≥2 subjects with `cloth_type=overall`)
   - Runs inference twice per subject: once with `segmentation_free=True`, once with `False`
   - Uses identical `FASHN_SEED` for both arms to isolate the variable
   - Saves outputs labeled `{subject}_segfree_true.jpg` and `{subject}_segfree_false.jpg`
   - Logs MD5 hashes and byte sizes for comparison
2. Run the script in the FASHN Docker container
3. Visually compare outputs on: dress silhouette accuracy, leg boundary quality, hand region
4. Document the preferred value with rationale
5. Update `_segmentation_free_for()` inline comment with A/B outcome
6. Update `docker-compose.yml` / `.env.example` with the chosen default

**Story 004 — Full-Resolution Model Image A/B**:

1. Create `docker/fashn/ab_model_resolution.py` — Script that:
   - Loads a model image at both thumbnail (~400×600) and full resolution
   - Runs inference with identical garment and seed for both
   - Saves outputs labeled `{subject}_thumbnail.jpg` and `{subject}_fullres.jpg`
   - Logs MD5 hashes, byte sizes, and inference timing
2. Run the script in the FASHN Docker container
3. Visually compare outputs on: hand boundary sharpness, leg skin texture, overall detail
4. If full-res shows meaningful improvement:
   - Verify `ModeloIA` model has an `image_key` field (currently only `thumbnail_key` confirmed)
   - Update `generate_vton.py` line 106: `model_key = modelo.image_key` (with fallback to `thumbnail_key`)
   - Update MinIO bucket reference from `model-thumbnails` to the full-res bucket
5. If no meaningful difference: document decision to keep thumbnail path

### Acceptance Criteria

- [ ] segmentation_free A/B result documented on ≥2 subjects; default updated in docker-compose.yml / .env.example
- [ ] Full-res vs thumbnail comparison documented; worker updated if meaningful improvement
- [ ] No regressions introduced by configuration changes
- [ ] `_segmentation_free_for()` inline comment updated with A/B rationale

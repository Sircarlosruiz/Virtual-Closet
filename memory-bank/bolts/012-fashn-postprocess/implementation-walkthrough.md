---
stage: implement
bolt: 012-fashn-postprocess
created: 2026-05-31T13:00:00Z
---

## Implementation Walkthrough: fashn-postprocess (A/B Evaluations)

### Summary

Created two automated A/B test scripts for evaluating FASHN configuration options: segmentation_free flag impact on one-piece garments, and model image resolution (thumbnail vs full-res) impact on output quality. Updated `_segmentation_free_for()` inline documentation with A/B methodology. Actual A/B execution deferred to GPU environment.

### Structure Overview

Two standalone A/B test scripts added to `docker/fashn/` for isolated variable testing. Scripts follow the same pattern: discover/load test images, run inference with controlled parameters, save labeled outputs for visual comparison. No changes to production code paths — A/B results will determine if configuration updates are needed.

### Completed Work

- [x] `docker/fashn/ab_segmentation_free.py` - A/B test script comparing segmentation_free=True vs False on ≥2 subjects
- [x] `docker/fashn/ab_model_resolution.py` - A/B test script comparing thumbnail vs full-res model input
- [x] `docker/fashn/main.py` - Updated `_segmentation_free_for()` docstring with A/B methodology and placeholder for results

### Key Decisions

- **Separate scripts per variable**: Each A/B test isolates a single variable (segmentation_free OR resolution) to avoid confounding effects
- **Identical seed enforcement**: Both scripts set `FASHN_SEED=42` to ensure the only difference between arms is the tested variable
- **Labeled output convention**: Outputs named `{subject}_{variable}_{value}.jpg` for easy visual comparison
- **Deferred worker update**: `generate_vton.py` not modified yet — will only update if full-res A/B shows meaningful improvement AND `image_key` field is added to `ModeloIA` model
- **Schema gap identified**: `ModeloIA` model currently only has `thumbnail_key` — no `image_key` field exists for full-res storage. If full-res wins the A/B, a migration will be needed

### Deviations from Plan

- **`ModeloIA.image_key` does not exist**: The plan assumed this field existed. It does not — only `thumbnail_key` is stored. If full-res A/B shows improvement, the following additional work is needed:
  1. Add `image_key` column to `modelo_ia` table (Alembic migration)
  2. Update `modelo_ia_service.py` upload flow to store both thumbnail and full-res
  3. Update `generate_vton.py` line 106 to use `image_key` with fallback to `thumbnail_key`

### Dependencies Added

None. A/B scripts use existing dependencies (PIL, NumPy, FASHN pipeline).

### Developer Notes

- **A/B execution requires GPU**: Both scripts must run inside the FASHN Docker container with GPU access
- **Test images required**: Place test images in `/app/test_images/` before running scripts
- **seg_free A/B**: Needs `subject_N_garment.jpg` + `subject_N_model.jpg` for N=1,2,3...
- **resolution A/B**: Needs `maria_fullres.jpg`, `maria_thumbnail.jpg`, `garment.jpg`
- **Visual inspection mandatory**: Automated scripts produce outputs and metrics, but final decision requires human visual comparison
- **Current default preserved**: `_segmentation_free_for("overall")` still returns `False` — will update after A/B results

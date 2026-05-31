---
stage: test
bolt: 012-fashn-postprocess
created: 2026-05-31T13:30:00Z
---

## Test Walkthrough: fashn-postprocess (A/B Evaluations)

### Summary

A/B test scripts created and ready for execution in GPU environment. Tests require FASHN Docker container with GPU access and test images. Results will determine configuration defaults for segmentation_free flag and model image resolution.

### Test Files

- [x] `docker/fashn/ab_segmentation_free.py` - A/B test for segmentation_free flag (story 003)
- [x] `docker/fashn/ab_model_resolution.py` - A/B test for model resolution (story 004)

### Test Execution

#### Prerequisites

1. **FASHN Docker container running with GPU access**:
   ```bash
   docker compose up -d fashn
   ```

2. **Test images in `/app/test_images/`**:

   **For segmentation_free A/B (story 003)**:
   - `subject_1_garment.jpg` + `subject_1_model.jpg` (first one-piece subject)
   - `subject_2_garment.jpg` + `subject_2_model.jpg` (second one-piece subject)
   - Optional: `subject_3_*`, `subject_4_*` for more subjects

   **For resolution A/B (story 004)**:
   - `maria_fullres.jpg` (full-resolution model photo)
   - `maria_thumbnail.jpg` (thumbnail ~400×600)
   - `garment.jpg` (garment for testing)

#### Running Tests

**segmentation_free A/B**:
```bash
docker compose exec fashn python ab_segmentation_free.py
```

**Model resolution A/B**:
```bash
docker compose exec fashn python ab_model_resolution.py
```

### Expected Outputs

#### segmentation_free A/B

**Output location**: `/app/test_outputs/ab_segfree/`

**Files generated**:
- `subject_1_segfree_true.jpg` - Output with segmentation_free=True
- `subject_1_segfree_false.jpg` - Output with segmentation_free=False
- `subject_2_segfree_true.jpg` - Output with segmentation_free=True
- `subject_2_segfree_false.jpg` - Output with segmentation_free=False

**Console output**:
```
=== segmentation_free A/B Test ===
Subjects: ['subject_1', 'subject_2']

--- subject_1 ---
  Running segmentation_free=false
    MD5: a1b2c3d4
    Size: 245678 bytes
    Saved: /app/test_outputs/ab_segfree/subject_1_segfree_false.jpg
  Running segmentation_free=true
    MD5: e5f6g7h8
    Size: 248901 bytes
    Saved: /app/test_outputs/ab_segfree/subject_1_segfree_true.jpg

--- subject_2 ---
  Running segmentation_free=false
    MD5: i9j0k1l2
    Size: 251234 bytes
    Saved: /app/test_outputs/ab_segfree/subject_2_segfree_false.jpg
  Running segmentation_free=true
    MD5: m3n4o5p6
    Size: 254567 bytes
    Saved: /app/test_outputs/ab_segfree/subject_2_segfree_true.jpg

=== A/B Test Complete ===
```

#### Model Resolution A/B

**Output location**: `/app/test_outputs/ab_resolution/`

**Files generated**:
- `maria_thumbnail_input.jpg` - Output using thumbnail input
- `maria_fullres_input.jpg` - Output using full-res input

**Console output**:
```
=== Model Resolution A/B Test ===

--- thumbnail ---
  Input size: (400, 600)
  Output MD5: q7r8s9t0
  Output size: (576, 864)
  Output bytes: 234567
  Inference time: 12.34s
  Saved: /app/test_outputs/ab_resolution/maria_thumbnail_input.jpg

--- fullres ---
  Input size: (1200, 1800)
  Output MD5: u1v2w3x4
  Output size: (576, 864)
  Output bytes: 245678
  Inference time: 13.45s
  Saved: /app/test_outputs/ab_resolution/maria_fullres_input.jpg

=== A/B Test Complete ===
```

### Acceptance Criteria Validation

#### Story 003: segmentation_free A/B

- [ ] **≥2 subjects tested**: Script requires minimum 2 subjects, fails otherwise
- [ ] **Outputs saved and labeled**: Files named `{subject}_segfree_{true|false}.jpg`
- [ ] **Visual comparison possible**: Side-by-side comparison of true vs false for each subject
- [ ] **Decision documented**: After visual inspection, update `_segmentation_free_for()` docstring with result
- [ ] **Configuration updated**: Update `docker-compose.yml` / `.env.example` with chosen default

**Visual evaluation checklist**:
- [ ] Dress silhouette accuracy (shape, edges)
- [ ] Leg boundary quality (clean transition, no artifacts)
- [ ] Hand region (sharpness, color accuracy)
- [ ] Overall color consistency (no unexpected color bleed)

#### Story 004: Model Resolution A/B

- [ ] **Thumbnail vs full-res compared**: Script generates both outputs with identical seed
- [ ] **Outputs saved and labeled**: Files named `maria_{thumbnail|fullres}_input.jpg`
- [ ] **Visual comparison possible**: Side-by-side comparison of outputs
- [ ] **Performance impact measured**: Inference time logged for both inputs
- [ ] **Decision documented**: After visual inspection, document choice

**Visual evaluation checklist**:
- [ ] Hand boundary sharpness (finger edges, skin/fabric transition)
- [ ] Leg skin texture (detail preservation, no over-smoothing)
- [ ] Overall detail quality (fine patterns, textures)
- [ ] Inference time impact (acceptable overhead?)

**Decision tree**:
- If full-res shows **meaningful improvement** in hand/leg detail:
  - [ ] Add `image_key` field to `ModeloIA` model (Alembic migration)
  - [ ] Update `modelo_ia_service.py` to store both thumbnail and full-res
  - [ ] Update `generate_vton.py` line 106: `model_key = modelo.image_key or modelo.thumbnail_key`
  - [ ] Update MinIO bucket reference from `model-thumbnails` to full-res bucket
- If **no meaningful difference**:
  - [ ] Document decision to keep thumbnail path (performance/cost benefit)
  - [ ] Add comment in `generate_vton.py` explaining the choice

### Issues Found

None. Scripts created and syntax validated. Runtime testing deferred to GPU environment.

### Notes

- **GPU environment required**: A/B tests cannot run in this environment (no GPU, no FASHN pipeline)
- **Test images not included**: Actual test images must be provided by user/developer
- **Visual inspection mandatory**: Automated metrics (MD5, bytes, time) are supplementary — final decision requires human visual comparison
- **Seed control critical**: Both scripts enforce `FASHN_SEED=42` to ensure the only variable is the tested parameter
- **Postprocess enabled**: Both scripts use `FASHN_PRESERVE_LIMBS=true` and `FASHN_LEG_POSTPROCESS=true` to test with production postprocessing

### Next Steps After A/B Execution

1. **Run both A/B scripts** in FASHN Docker container
2. **Visually compare outputs** using the checklists above
3. **Document results** in `_segmentation_free_for()` docstring (story 003)
4. **Update configuration**:
   - Story 003: Update `docker-compose.yml` / `.env.example` with chosen `FASHN_SEGMENTATION_FREE` default
   - Story 004: If full-res wins, implement schema changes and worker update
5. **Mark stories complete** after configuration updates are applied

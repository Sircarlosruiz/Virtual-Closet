---
unit: 001-fashn-postprocess
intent: 003-fashn-provider-upgrade
phase: inception
status: complete
unit_type: backend
default_bolt_type: simple-construction-bolt
created: 2026-05-31T00:00:00.000Z
updated: 2026-05-31T00:00:00.000Z
---

# Unit Brief: fashn-postprocess

## Purpose

Tune `docker/fashn/postprocess.py` and `docker/fashn/main.py` to eliminate two visible artifact types in FASHN v1.5 output — finger/hand blending into dress fabric and flat skin patches on legs — and validate provider configuration options (segmentation_free, input resolution).

## Scope

### In Scope
- `_limb_mask_from_original()` — tighten garment label exclusion to eliminate original-dress color bleed under hands
- `preserve_hands_and_arms()` — tune blend boundary; document or expose `FASHN_PRESERVE_LIMBS=false` escape hatch
- `_original_wearing_long_pants()` — validate + tune `_PANTS_AREA_RATIO` and artifact thresholds on a real long-pants subject
- `fix_one_piece_legs()` — validate luminance/distance thresholds (`lum < 130`, `dist > 28`) and blur kernel sizes
- `_segmentation_free_for()` — A/B test `segmentation_free=False` vs `True` for `overall` cloth type on ≥2 subjects
- Celery worker full-res input A/B (compare `thumbnail_key` vs full-res key)
- All threshold values documented as named constants with inline rationale

### Out of Scope
- Changes to the `/predict` or `/classify` API contract
- New human parser model or hand-specific segmentation model
- Deployment reliability and Docker ops (→ unit 002)
- Multi-subject test suite documentation (→ unit 002)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Hand compositing: eliminate blurry finger edges and original-dress color bleed under hands | Must |
| FR-2 | Long-pants branch: validate fix_one_piece_legs on ≥1 long-pants subject; tune thresholds | Must |
| FR-5 | segmentation_free A/B: confirm best value for one-pieces on ≥2 subjects; document in config | Should |
| FR-6 | Full-res model image: A/B thumbnail vs. full-res on María; update worker if improvement is meaningful | Could |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| Person image | Original model photo before VTON | numpy array (H×W×3), aligned to generated |
| Generated image | Raw FASHN output before postprocess | numpy array (H×W×3) |
| Segmentation mask | Parser output (label IDs per pixel) | numpy array (H×W), `FASHN_LABELS_TO_IDS` labels |
| Limb mask | Binary mask of hand/arm pixels from original | numpy array (H×W), skin-gated + garment-excluded |
| Pants mask | Boolean — whether original has long pants in lower body region | derived from segmentation |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `_limb_mask_from_original` | Segment hands from original; exclude garment pixels | original numpy array | binary mask |
| `_blend_original_mask` | Alpha-blend original over generated using soft mask | orig, gen, mask, blur_kernel | blended numpy array |
| `_original_wearing_long_pants` | Detect substantial pants coverage in lower body | original numpy array | bool |
| `fix_one_piece_legs` | Repair dark pant artifacts; restore feet | original, generated Image | Image |
| `_segmentation_free_for` | Determine segmentation_free flag by cloth_type | cloth_type str, env override | bool |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 4 |
| Must Have | 2 |
| Should Have | 1 |
| Could Have | 1 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-hand-compositing-tuning | Tune hand compositing to eliminate artifacts | Must | Planned |
| 002-long-pants-threshold-validation | Validate and tune long-pants detection thresholds | Must | Planned |
| 003-segmentation-free-ab-test | A/B test segmentation_free for one-pieces | Should | Planned |
| 004-full-resolution-model-image | Compare thumbnail vs full-res model input | Could | Planned |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| None | Self-contained; modifies only docker/fashn/ files |

### Depended By
| Unit | Reason |
|------|--------|
| 002-fashn-validation | Test suite results are only meaningful after code fixes are in place |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| FashnHumanParser | Provides label IDs for hand/garment segmentation | Medium — `hands` label must be distinct from `arms` |
| FASHN TryOnPipeline | Target of segmentation_free parameter changes | Low — API stable |

---

## Technical Context

### Suggested Technology
- Python 3.x, OpenCV (`cv2`), NumPy, Pillow — already in use
- `FashnHumanParser` from `fashn_human_parser` — already in use
- `FASHN_LABELS_TO_IDS` from `fashn_vton.preprocessing` — verify all needed labels are present

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| postprocess.py ↔ main.py | Internal import | `postprocess_tryon()` called in `/predict` |
| postprocess.py ↔ FashnHumanParser | Library call | `_get_parser().predict(img)` → label array |

### Data Storage
| Data | Type | Notes |
|------|------|-------|
| Test output images | JPEG files | Stored in `.agents/reports/` or `docs/imgs/` for reference |

---

## Constraints

- Human parser must run on CPU (reserved; GPU is for diffusion pipeline)
- Mask operations must complete in < 3s total (hand + conditional check)
- `FASHN_PRESERVE_LIMBS` and `FASHN_LEG_POSTPROCESS` env vars must remain as kill switches
- Threshold changes must not break upper/lower cloth types (those return early before any leg logic)

---

## Success Criteria

### Functional
- [ ] No original-dress color bleed visible under/around hands in FR-1 test output
- [ ] Finger edges are visually distinct from dress fabric in FR-1 test output
- [ ] `fix_one_piece_legs` runs on long-pants subject and eliminates dark artifacts (FR-2)
- [ ] No flat-color patches introduced on legs of long-pants subject after fix (FR-2)
- [ ] segmentation_free A/B result documented and default updated (FR-5)
- [ ] Full-res vs thumbnail decision documented (FR-6)

### Non-Functional
- [ ] Postprocess total overhead < 3s per call
- [ ] All threshold values are named constants (no magic numbers)
- [ ] Zero regressions on existing María bare-legs output

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 011-fashn-postprocess | simple-construction-bolt | 001, 002 | Core Must fixes: hand compositing + long-pants validation |
| 012-fashn-postprocess | simple-construction-bolt | 003, 004 | Should/Could: A/B evaluations for seg_free and full-res |

---

## Notes

- v4 baseline: `fashn_v4_maria.jpg` (md5: c3d395d6) — María + producto_1, postprocess v4
- The `FASHN_LABELS_TO_IDS` key `"hands"` must be verified to exist as a distinct class (not merged with `"arms"`) before tuning `_limb_mask_from_original`
- Changing `segmentation_free` affects the internal garment mask FASHN uses — not a trivial parameter; document A/B results clearly

---
stage: plan
bolt: 011-fashn-postprocess
created: 2026-05-31T10:00:00Z
---

## Implementation Plan: fashn-postprocess

### Objective

Tune `docker/fashn/postprocess.py` so that (1) hand compositing produces a clean skin/fabric boundary with no original-garment color bleed, and (2) the `fix_one_piece_legs` path is validated and thresholds documented on a real long-pants subject.

### Deliverables

1 - **Tightened garment exclusion in `_limb_mask_from_original()`** — ensure all garment label IDs zero out the preserve mask before blending, preventing dress/skirt color bleed under hands
2 - **Tuned blend boundary** — evaluate and adjust `blur_kernel` in `preserve_hands_and_arms()` (currently 15) and erosion kernel (currently 3x3) for sharper finger edges
3 - **Named threshold constants** — extract magic numbers in `fix_one_piece_legs()` (`lum < 130`, `dist > 28`, `d=7`, `sigmaColor=50`, `sigmaSpace=50`) into named constants with inline rationale
4 - **Validated `_PANTS_AREA_RATIO`** — confirm threshold fires correctly on a real long-pants subject; adjust if needed
5 - **Validated `fix_one_piece_legs()`** — run on long-pants subject, verify dark artifacts eliminated without introducing flat-color patches
6 - **Regression check** — confirm v4 Mara baseline (md5: c3d395d6) is unchanged or improved

### Dependencies

- **FashnHumanParser** (CPU): provides label IDs for hand/garment segmentation. Must verify `FASHN_LABELS_TO_IDS["hands"]` exists as a distinct class from `"arms"`.
- **FASHN v4 baseline image** (`fashn_v4_maria.jpg`, md5: c3d395d6): regression reference for Mara + producto_1.
- **Long-pants test subject image**: needed to validate `_original_wearing_long_pants()` and `fix_one_piece_legs()`. Must be sourced before Stage 2.
- **GPU environment**: FASHN pipeline runs on GPU; postprocess validation requires running the full `/predict` flow.

### Technical Approach

**Story 001 — Hand Compositing Tuning**:

1. Verify `FASHN_LABELS_TO_IDS["hands"]` is a distinct key (not merged with `"arms"`) by inspecting the label map at runtime
2. Review `_limb_mask_from_original()`: the garment exclusion line `garment = np.isin(seg, [ids["dress"], ids["skirt"], ids["pants"], ids["top"]])` already covers all garment types — verify it correctly zeroes the mask in overlap regions
3. Evaluate erosion kernel size: current 3x3 with 1 iteration may not shrink enough away from dress boundary. Consider increasing to 5x5 or adding an extra erosion iteration
4. Evaluate `blur_kernel=15` in `preserve_hands_and_arms()`: reducing to 11 or 9 may sharpen finger edges without introducing hard boundaries
5. Run determinism check: same inputs + `FASHN_SEED=42` → confirm MD5 stability before comparing A vs B
6. Visual comparison: before/after on Mara baseline to confirm no regression

**Story 002 — Long-Pants Threshold Validation**:

1. Extract magic numbers into named constants at module level:
   - `_DARK_PIXEL_LUMINANCE = 130` — luminance ceiling for artifact detection
   - `_SKIN_COLOR_DISTANCE = 28` — minimum color distance from skin reference
   - `_BILATERAL_FILTER_D = 7` — bilateral filter diameter for repair band smoothing
   - `_BILATERAL_SIGMA_COLOR = 50` — color similarity sigma
   - `_BILATERAL_SIGMA_SPACE = 50` — spatial proximity sigma
   - `_REPAIR_TOP_OFFSET_FACTOR = 0.012` — vertical offset below garment hem
   - `_REPAIR_BAND_END = 0.88` — fraction of image height where repair band ends
2. Add inline comments documenting empirical rationale for each constant
3. Run `_original_wearing_long_pants()` on a real long-pants subject and log `pants_ratio` to confirm it exceeds `_PANTS_AREA_RATIO = 0.025`
4. Run `fix_one_piece_legs()` on the same subject and visually inspect output for dark artifact elimination and absence of flat-color patches
5. If thresholds need adjustment, update constants and re-test

### Acceptance Criteria

- [ ] No original-dress color visible under/around hands in test output
- [ ] Finger edges visually distinct from dress fabric
- [ ] `fix_one_piece_legs` validated on at least 1 long-pants subject — dark artifacts eliminated
- [ ] No flat-color patches introduced on legs after fix
- [ ] All threshold constants documented with inline rationale (no magic numbers)
- [ ] Zero regressions on v4 Mara baseline (md5: c3d395d6)
- [ ] `FASHN_PRESERVE_LIMBS=false` escape hatch verified — skips `preserve_hands_and_arms()` entirely

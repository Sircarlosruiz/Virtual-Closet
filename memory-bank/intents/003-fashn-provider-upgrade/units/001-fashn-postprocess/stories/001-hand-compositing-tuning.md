---
id: 001-hand-compositing-tuning
unit: 001-fashn-postprocess
intent: 003-fashn-provider-upgrade
status: complete
priority: must
created: 2026-05-31T00:00:00.000Z
assigned_bolt: 011-fashn-postprocess
implemented: true
---

# Story: 001-hand-compositing-tuning

## User Story

**As a** mayorista viewing VTON results
**I want** the model's hands and fingers to look sharp and natural against the generated dress
**So that** the try-on image looks professional and I can use it in my catalog without retouching

## Acceptance Criteria

- [ ] **Given** a model photo where hands rest on or near the dress area, **When** /predict runs with `cloth_type=overall`, **Then** the output shows no original-dress color (e.g., red) bleeding under or around the hands
- [ ] **Given** the same model photo, **When** postprocess runs, **Then** finger edges are visually distinct from dress fabric — no "melted fingers" appearance
- [ ] **Given** `_limb_mask_from_original()` executes, **When** the original wears a dress/skirt, **Then** all garment label IDs (`dress`, `skirt`, `pants`, `top`) are excluded from the preserve mask before blending
- [ ] **Given** `FASHN_PRESERVE_LIMBS=false` is set, **When** /predict runs, **Then** `preserve_hands_and_arms()` is skipped entirely and the raw FASHN output is used
- [ ] **Given** the v4 María baseline (md5: c3d395d6), **When** the same inputs run after tuning, **Then** the output either matches or shows measurably fewer hand artifacts (no regression on previously passing areas)

## Technical Notes

- `_limb_mask_from_original()` in `postprocess.py` currently segments `hands` label and applies `_skin_like_mask`. Verify `FASHN_LABELS_TO_IDS["hands"]` exists as a distinct class — not merged with `"arms"`.
- The garment exclusion `garment = np.isin(seg, [ids["dress"], ids["skirt"], ids["pants"], ids["top"]])` must zero out the preserve mask in those regions. If the original wears a dress and hands overlap the dress region, the mask should narrow to only exposed skin, not the dress-covered area.
- Consider tightening the erosion kernel in `_limb_mask_from_original` (currently 3×3) to shrink the preserved region away from the dress boundary.
- `blur_kernel=15` in `preserve_hands_and_arms` controls blend softness — reducing may sharpen edges.

## Dependencies

### Requires
- None (first story in unit)

### Enables
- 002-long-pants-threshold-validation (shares parser infrastructure)
- 002-multi-subject-test-suite (unit 002) — needs working hand compositing before multi-subject runs

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| No hands detected by parser | `_limb_mask_from_original` returns all-zero mask; `preserve_hands_and_arms` returns `generated` unchanged; INFO log: "No hands/arms detected" |
| `FASHN_PRESERVE_LIMBS=false` | `preserve_hands_and_arms` not called; raw FASHN output used for hands |
| Hands fully behind dress (full occlusion) | Parser may not detect hands; mask is zero; no compositing — acceptable |
| Original has no garment (bare torso) | Garment exclusion has no effect; mask covers full hand region |

## Out of Scope

- Pre-generation hand masking (FASHN v1.5 API does not support it)
- Arms restoration (only hands/fingers are the visible artifact — arms are usually behind the dress)
- Face or hair restoration

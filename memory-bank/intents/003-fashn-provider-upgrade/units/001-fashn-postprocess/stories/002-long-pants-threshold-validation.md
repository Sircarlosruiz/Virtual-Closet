---
id: 002-long-pants-threshold-validation
unit: 001-fashn-postprocess
intent: 003-fashn-provider-upgrade
status: complete
priority: must
created: 2026-05-31T00:00:00.000Z
assigned_bolt: 011-fashn-postprocess
implemented: true
---

# Story: 002-long-pants-threshold-validation

## User Story

**As a** mayorista who photographed a model wearing long pants
**I want** the VTON output to replace the pants with the new dress cleanly, without dark blocks or flat-color patches
**So that** I can generate professional catalog images from subjects wearing pants, not just bare-legged subjects

## Acceptance Criteria

- [ ] **Given** a model photo with substantial long-pants coverage in the lower body, **When** /predict runs with `cloth_type=overall`, **Then** `_original_wearing_long_pants()` returns `True` and `fix_one_piece_legs()` is called
- [ ] **Given** `fix_one_piece_legs()` runs on a long-pants subject, **When** the output is inspected, **Then** dark pant-block artifacts are eliminated below the garment hem
- [ ] **Given** `fix_one_piece_legs()` runs, **When** the output is inspected, **Then** no flat-color skin patches are visible — leg texture and shadows are preserved
- [ ] **Given** the current `_PANTS_AREA_RATIO = 0.025` threshold, **When** the pants-ratio is measured for the long-pants test subject, **Then** it exceeds 0.025 — confirming the threshold fires correctly
- [ ] **Given** threshold constants `_PANTS_AREA_RATIO`, `lum < 130`, `dist > 28`, **When** they are reviewed after validation, **Then** each has an inline comment documenting the empirical rationale and the test subject used to set it

## Technical Notes

- `_original_wearing_long_pants()` measures `pants_ratio` in the lower body region (`y > 42%`, `x: 15%–85%`). Log output: `pants ratio=X.XXX`. Threshold `_PANTS_AREA_RATIO = 0.025` was set without a real pants test case — may need adjustment.
- `fix_one_piece_legs()` uses `lum < 130` (dark pixel detection) and `dist > 28` (color distance from skin reference) to identify artifact pixels. These values were empirical and may produce flat-color patches if too aggressive on non-artifact pixels.
- Bilateral filter (`d=7, sigmaColor=50, sigmaSpace=50`) smooths the repaired band — if values are too high, it over-smooths and creates visible boundary.
- Run at least one real test with a long-pants model photo and inspect output visually before finalizing thresholds.

## Dependencies

### Requires
- 001-hand-compositing-tuning (shares parser initialization — `_get_parser()` is a singleton)

### Enables
- 002-multi-subject-test-suite (unit 002) — long-pants subject is part of the required test matrix

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Pants barely visible (shorts, cropped pants) | `pants_ratio` below threshold; `fix_one_piece_legs` not called; FASHN legs used as-is |
| Very dark dress (not pants) generates dark legs | Luminance check may false-positive; tuning `lum` threshold or adding color-gate needed |
| No garment hem detected by `_estimate_garment_hem` | Returns `restore_feet_only`; no flat-color repair applied |
| Parser fails to label pants correctly | `pants_ratio = 0`; bare-legs path taken; no fix applied — must be validated visually |

## Out of Scope

- Short pants / shorts (threshold handles this by requiring substantial lower-body coverage)
- Skirts in the original photo (skirt → dress transition, different garment class)

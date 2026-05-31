---
id: 004-full-resolution-model-image
unit: 001-fashn-postprocess
intent: 003-fashn-provider-upgrade
status: complete
priority: could
created: 2026-05-31T00:00:00.000Z
assigned_bolt: 012-fashn-postprocess
implemented: true
---

# Story: 004-full-resolution-model-image

## User Story

**As a** mayorista reviewing VTON output quality
**I want** the FASHN pipeline to receive the highest-quality model photo available
**So that** fine details like finger edges and leg skin texture are as accurate as possible in the output

## Acceptance Criteria

- [ ] **Given** the same model photo stored both as thumbnail (`thumbnail_key`, ~400×600) and full resolution, **When** both are sent to /predict with identical garment and seed, **Then** both outputs are saved and compared visually for hand and leg quality
- [ ] **Given** the comparison, **When** full-res shows a meaningful improvement in hand boundary sharpness or leg texture, **Then** the Celery worker is updated to fetch and pass the full-res image key instead of the thumbnail
- [ ] **Given** the comparison, **When** there is no meaningful quality difference, **Then** the thumbnail path is kept and the decision is documented with rationale
- [ ] **Given** the decision, **When** implemented, **Then** it is reflected in the worker code or documented as a deliberate choice in the relevant code comment

## Technical Notes

- The Celery worker currently resolves `modelo.thumbnail_key` (roughly 400×600 px) when calling the FASHN container. The full-res key would be `modelo.image_key` (original upload resolution).
- FASHN internally resizes inputs to 576×864 before diffusion — sending a larger image allows FASHN to downsample with better anti-aliasing, which may improve edge fidelity.
- Pre-signed URLs expire in 15 minutes — ensure the worker fetches fresh URLs before each call regardless of key used.
- Larger input = slightly more memory and preprocessing time — measure and document the overhead.

## Dependencies

### Requires
- 001-hand-compositing-tuning (hand quality baseline before comparing)

### Enables
- 002-multi-subject-test-suite (unit 002) — full-res decision should be made before running the multi-subject suite

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Full-res image unavailable (old upload) | Worker falls back to thumbnail; log a warning |
| Full-res exceeds FASHN memory limits | FASHN resizes internally; test to confirm no OOM |

## Out of Scope

- Changing FASHN's internal generation resolution (576×864 is set by the model, not configurable)
- Image upscaling or super-resolution pre-processing

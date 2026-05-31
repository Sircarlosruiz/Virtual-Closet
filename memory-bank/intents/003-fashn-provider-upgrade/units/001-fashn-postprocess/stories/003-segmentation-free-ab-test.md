---
id: 003-segmentation-free-ab-test
unit: 001-fashn-postprocess
intent: 003-fashn-provider-upgrade
status: complete
priority: should
created: 2026-05-31T00:00:00.000Z
assigned_bolt: 012-fashn-postprocess
implemented: true
---

# Story: 003-segmentation-free-ab-test

## User Story

**As a** developer maintaining the FASHN integration
**I want** a documented A/B comparison of segmentation_free=True vs False for one-piece garments
**So that** the default is set to the value that produces consistently better output, with evidence to justify the choice

## Acceptance Criteria

- [ ] **Given** ≥2 test subjects with `cloth_type=overall`, **When** each is run with `FASHN_SEGMENTATION_FREE=true` and again with `FASHN_SEGMENTATION_FREE=false`, **Then** both outputs are saved and labeled for visual comparison
- [ ] **Given** the A/B outputs, **When** compared on dress silhouette accuracy, leg boundary quality, and hand region, **Then** the preferred value is identified and the rationale documented
- [ ] **Given** the A/B result, **When** the decision is made, **Then** `docker-compose.yml` and/or `.env.example` reflect the chosen default for `FASHN_SEGMENTATION_FREE`
- [ ] **Given** the current code in `_segmentation_free_for()`, **When** reviewed after the A/B, **Then** the inline comment documents the A/B outcome and test subjects used to determine the default

## Technical Notes

- Current behavior: `_segmentation_free_for("overall")` returns `False` (garment segmentation on). This was set heuristically — `False` means FASHN uses its internal garment mask to determine where to paint the new garment.
- `segmentation_free=True` disables FASHN's internal mask — the diffusion model gets more freedom but may bleed color into unexpected regions.
- A/B test procedure: set `FASHN_SEGMENTATION_FREE=true` (or `false`) in docker-compose, rebuild, run identical inputs, compare output JPEGs visually and by MD5.
- Use the same `FASHN_SEED` for both runs to ensure the only variable is the `segmentation_free` flag.

## Dependencies

### Requires
- 001-hand-compositing-tuning (002 stable code baseline before A/B)
- 002-long-pants-threshold-validation (stable baseline)

### Enables
- 002-multi-subject-test-suite (unit 002) — A/B result determines the default used in the test suite

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| A/B shows no meaningful difference | Document as "no measurable difference"; keep current default (False) |
| One value clearly better on dress shape, worse on legs | Document trade-off; choose based on which artifact is more visible to mayoristas |

## Out of Scope

- A/B for `upper` or `lower` cloth types (segmentation_free defaults to True for those — not changing)
- Changing the FASHN diffusion model steps or guidance as part of this story

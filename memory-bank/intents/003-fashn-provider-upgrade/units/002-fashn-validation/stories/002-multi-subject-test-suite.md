---
id: 002-multi-subject-test-suite
unit: 002-fashn-validation
intent: 003-fashn-provider-upgrade
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 013-fashn-validation
implemented: false
---

# Story: 002-multi-subject-test-suite

## User Story

**As a** developer validating FASHN postprocess quality
**I want** a structured test suite with ≥3 real subjects covering key failure scenarios
**So that** I can confirm the hand compositing and leg repair fixes work across diverse poses and body types — not just for María

## Acceptance Criteria

- [ ] **Given** the test suite, **When** counted, **Then** ≥3 distinct real subject photos are present in the test directory (`docs/imgs/test-subjects/` or equivalent)
- [ ] **Given** each subject, **When** run through /predict, **Then** at least one run uses `cloth_type=overall` and at least one subject has hands near/on the garment area
- [ ] **Given** ≥1 subject, **When** run through /predict, **Then** the subject is wearing long pants in the original photo (validates the `fix_one_piece_legs` path)
- [ ] **Given** all runs complete, **When** results are documented, **Then** a `test-results.md` file is committed that includes: subject name, garment used, FASHN_SEED, output MD5, and pass/fail for `hand_boundary` and `leg_quality` artifact checks
- [ ] **Given** all subjects in `test-results.md`, **When** reviewed, **Then** all entries show `hand_boundary: pass` and `leg_quality: pass` (zero failures after postprocess tuning from unit 001)

## Technical Notes

- Test coverage matrix (minimum):

  | Subject | Cloth Type | Hand Position | Leg Coverage | Purpose |
  |---------|-----------|---------------|--------------|---------|
  | María | overall | on/near dress | bare legs | Baseline (existing) |
  | Subject 2 | overall | neutral / away from dress | bare legs | Validate no-occlusion case |
  | Subject 3 | overall | on/near dress | long pants | Validate fix_one_piece_legs path |

- Photos must be licensed (own shots, stock with commercial license, or from app uploads with permission)
- Output images committed to `.agents/reports/` or `docs/imgs/test-output/` with naming: `{subject}_{garment}_{seed}.jpg`
- `test-results.md` format:

  ```markdown
  | Subject | Garment | Seed | Output MD5 | hand_boundary | leg_quality | Notes |
  |---------|---------|------|------------|---------------|-------------|-------|
  | maria   | producto_1 | 42 | c3d395d6 | pass | pass | v4 baseline |
  ```

- Use `FASHN_SEED=42` for reproducibility; document any seed changes.

## Dependencies

### Requires
- 001-container-deployment-reliability (must have reliable container before running test suite)
- 001-hand-compositing-tuning (unit 001, bolt 011) — fixes must be in place before running suite
- 002-long-pants-threshold-validation (unit 001, bolt 011) — long-pants fix must be ready

### Enables
- Production deployment decision — test suite is the final quality gate

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Cannot source a licensed long-pants subject photo | Document blocker in test-results.md; use available subjects; flag as open item |
| A subject shows unexpected artifacts not covered by FR-1/FR-2 | Document in test-results.md as `new_artifact: <description>`; open a new story if needed |
| Output MD5 changes between identical runs | Indicates non-determinism — investigate before recording results |

## Out of Scope

- Automated regression testing (CI) — this is a manual eval suite
- Quantitative image quality metrics (SSIM, FID) — visual inspection is sufficient for MVP
- More than 3 subjects — minimum viable validation; expand later if needed

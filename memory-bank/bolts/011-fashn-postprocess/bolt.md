---
id: 011-fashn-postprocess
unit: 001-fashn-postprocess
intent: 003-fashn-provider-upgrade
type: simple-construction-bolt
status: complete
stories:
  - 001-hand-compositing-tuning
  - 002-long-pants-threshold-validation
created: 2026-05-31T00:00:00.000Z
started: 2026-05-31T10:00:00.000Z
completed: "2026-05-31T23:52:10Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-05-31T10:30:00.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-05-31T11:00:00.000Z
    artifact: implementation-walkthrough.md
requires_bolts: []
enables_bolts:
  - 012-fashn-postprocess
  - 013-fashn-validation
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 011-fashn-postprocess

## Overview

First postprocess bolt — fixes the two visible artifact types in FASHN v4 output: hand/finger compositing boundary issues (original-dress color bleed) and the long-pants detection + threshold tuning for the `fix_one_piece_legs` path (currently untested on a real subject).

## Objective

Tune `postprocess.py` so that (1) hand compositing produces a clean skin/fabric boundary with no original-garment color bleed, and (2) the `fix_one_piece_legs` path is validated and thresholds documented on a real long-pants subject.

## Stories Included

- **001-hand-compositing-tuning**: Eliminate blurry finger edges and original-dress color bleed under hands (Must)
- **002-long-pants-threshold-validation**: Validate and tune long-pants detection thresholds on real subject (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. plan**: Pending → implementation-plan.md
- [ ] **2. implement**: Pending → implementation-walkthrough.md
- [ ] **3. test**: Pending → test-walkthrough.md

## Dependencies

### Requires
- None (first bolt in intent)

### Enables
- 012-fashn-postprocess (A/B evaluations require stable code baseline)
- 013-fashn-validation (test suite requires hand + leg fixes in place)

## Success Criteria

- [ ] No original-dress color visible under/around hands in test output
- [ ] Finger edges visually distinct from dress fabric
- [ ] `fix_one_piece_legs` validated on ≥1 long-pants subject — dark artifacts eliminated
- [ ] No flat-color patches introduced on legs after fix
- [ ] All threshold constants documented with inline rationale
- [ ] Zero regressions on v4 María baseline (md5: c3d395d6)

## Notes

- Start by verifying `FASHN_LABELS_TO_IDS["hands"]` exists as a distinct class before tuning the mask
- Run determinism check after each change: same inputs + `FASHN_SEED=42` → confirm MD5 stability before comparing A vs B
- v4 baseline: `fashn_v4_maria.jpg` (md5: c3d395d6) is the regression reference

---
id: 013-fashn-validation
unit: 002-fashn-validation
intent: 003-fashn-provider-upgrade
type: simple-construction-bolt
status: complete
stories:
  - 001-container-deployment-reliability
  - 002-multi-subject-test-suite
created: 2026-05-31T00:00:00.000Z
started: 2026-05-31T14:00:00.000Z
completed: "2026-06-01T00:01:02Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-05-31T14:15:00.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-05-31T14:30:00.000Z
    artifact: implementation-walkthrough.md
  - name: test
    completed: 2026-05-31T14:45:00.000Z
    artifact: test-walkthrough.md
requires_bolts:
  - 011-fashn-postprocess
  - 012-fashn-postprocess
enables_bolts: []
requires_units: []
blocks: false
complexity:
  avg_complexity: 1
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 3
---

# Bolt: 013-fashn-validation

## Overview

Final validation bolt — fixes the stale-container deployment issue and runs the multi-subject test suite (≥3 real subjects) to confirm that postprocess fixes from bolts 011 and 012 hold across diverse poses, body types, and garment scenarios.

## Objective

Ensure the FASHN container always serves the latest code after a rebuild, and document test results for ≥3 subjects covering the key artifact failure modes (hand occlusion, bare legs, long pants). This is the quality gate before production deployment.

## Stories Included

- **001-container-deployment-reliability**: Kill orphan process; add version logging; document restart procedure (Must)
- **002-multi-subject-test-suite**: Source ≥3 real subjects; run and document test suite (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. plan**: Pending → implementation-plan.md
- [ ] **2. implement**: Pending → implementation-walkthrough.md
- [ ] **3. test**: Pending → test-walkthrough.md

## Dependencies

### Requires
- 011-fashn-postprocess (hand + leg code fixes must be in place)
- 012-fashn-postprocess (A/B defaults must be set before running test suite)

### Enables
- None (final bolt — construction complete for this intent)

## Success Criteria

- [ ] Rebuild → new container always serves requests (confirmed by version log + MD5 change)
- [ ] No orphan process binds :8002 after compose up
- [ ] Kill/restart procedure documented in Makefile or ops runbook
- [ ] ≥3 subjects tested; test-results.md committed with pass/fail per artifact
- [ ] All subjects show `hand_boundary: pass` and `leg_quality: pass`

## Notes

- Long-pants subject photo is required for this bolt — must be sourced before starting
- Test suite is manual (visual inspection + MD5 logging) — not automated CI
- `test-results.md` is the final artifact — committed to repo as evidence of quality validation
- After this bolt completes, intent is ready for Operations Agent

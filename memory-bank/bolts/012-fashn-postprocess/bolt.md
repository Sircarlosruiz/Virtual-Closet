---
id: 012-fashn-postprocess
unit: 001-fashn-postprocess
intent: 003-fashn-provider-upgrade
type: simple-construction-bolt
status: complete
stories:
  - 003-segmentation-free-ab-test
  - 004-full-resolution-model-image
created: 2026-05-31T00:00:00.000Z
started: 2026-05-31T12:00:00.000Z
completed: "2026-05-31T23:55:09Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-05-31T12:30:00.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-05-31T13:00:00.000Z
    artifact: implementation-walkthrough.md
  - name: test
    completed: 2026-05-31T13:30:00.000Z
    artifact: test-walkthrough.md
requires_bolts:
  - 011-fashn-postprocess
enables_bolts:
  - 013-fashn-validation
requires_units: []
blocks: false
complexity:
  avg_complexity: 1
  avg_uncertainty: 2
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 012-fashn-postprocess

## Overview

Second postprocess bolt — evaluates two provider-level configuration options via A/B testing: `segmentation_free` flag for one-piece garments, and model input resolution (thumbnail vs. full-res). Results determine the documented defaults for the FASHN deployment.

## Objective

Run controlled A/B tests to determine (1) whether `segmentation_free=False` or `True` produces better one-piece output across ≥2 subjects, and (2) whether passing full-resolution model images to FASHN improves hand and leg detail. Document and implement the winning configuration.

## Stories Included

- **003-segmentation-free-ab-test**: A/B test segmentation_free for one-pieces on ≥2 subjects (Should)
- **004-full-resolution-model-image**: Compare thumbnail vs. full-res model input on María (Could)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. plan**: Pending → implementation-plan.md
- [ ] **2. implement**: Pending → implementation-walkthrough.md
- [ ] **3. test**: Pending → test-walkthrough.md

## Dependencies

### Requires
- 011-fashn-postprocess (stable code baseline before running A/B tests)

### Enables
- 013-fashn-validation (final test suite uses the chosen defaults from A/B results)

## Success Criteria

- [ ] segmentation_free A/B result documented on ≥2 subjects; default updated in docker-compose.yml / .env.example
- [ ] Full-res vs thumbnail comparison documented; worker updated if meaningful improvement
- [ ] No regressions introduced by configuration changes
- [ ] `_segmentation_free_for()` inline comment updated with A/B rationale

## Notes

- Use same `FASHN_SEED` for both A/B arms to isolate the variable being tested
- Output images from both arms saved and labeled for reference in `.agents/reports/`
- If no meaningful difference is found in either A/B, document explicitly and keep current defaults

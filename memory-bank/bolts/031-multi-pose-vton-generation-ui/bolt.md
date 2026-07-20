---
id: 031-multi-pose-vton-generation-ui
unit: 003-multi-pose-vton-generation-ui
intent: 006-multi-pose-vton-generation
type: simple-construction-bolt
status: complete
stories:
  - 001-model-pose-management-ui
  - 002-pose-selection-submission-ui
created: 2026-07-17T00:00:00.000Z
started: 2026-07-18T16:48:52.000Z
completed: "2026-07-18T16:59:15Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-07-18T16:48:52.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-07-18T16:48:52.000Z
    artifact: implementation-walkthrough.md
requires_bolts:
  - 030-pose-set-service
enables_bolts:
  - 032-multi-pose-vton-generation-ui
requires_units:
  - 001-model-pose-service
  - 002-pose-set-service
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 031-multi-pose-vton-generation-ui

## Overview

Implements model/pose management and the pose-aware submission flow — the two entry-point pages a mayorista uses before viewing results.

## Objective

Mayorista can create a model, upload up to 3 pose photos, then select a garment + that model and deselect poses before submitting.

## Stories Included

- **001-model-pose-management-ui**: Model & Pose Management UI (Must)
- **002-pose-selection-submission-ui**: Pose Deselection & Submission UI (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Implementation plan for `ModelPoseManagementPage` and pose selection step in the submission flow → `implementation-plan.md`
- [ ] **2. Implement**: React components, API integration with `001-model-pose-service` and `002-pose-set-service`
- [ ] **3. Test**: Interaction tests — pose type disabling, min-1-selected enforcement, legacy single-pose passthrough → `test-walkthrough.md`

## Dependencies

### Requires
- 030-pose-set-service (`POST /api/pose-sets` must be available)

### Enables
- 032-multi-pose-vton-generation-ui (result view redirects here after submit)

## Success Criteria

- [ ] Mayorista can create a model and upload poses with duplicate types visually disabled
- [ ] Pose selection defaults to all-selected, submit disabled at 0 selected
- [ ] Legacy single-pose models submit with no pose-selection step shown
- [ ] Submit redirects to the pose set result view with the returned `pose_set_id`

## Notes

Reuse existing garment/model thumbnail and cloth-type selector components from `003-vton-pipeline-ui` and `002-batch-vton-generation-ui` to keep UI consistent.

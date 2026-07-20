---
id: 032-multi-pose-vton-generation-ui
unit: 003-multi-pose-vton-generation-ui
intent: 006-multi-pose-vton-generation
type: simple-construction-bolt
status: complete
stories:
  - 003-pose-set-result-view
created: 2026-07-17T00:00:00.000Z
started: 2026-07-18T16:48:52.000Z
completed: "2026-07-18T19:51:03Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-07-18T16:48:52.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-07-18T16:48:52.000Z
    artifact: implementation-walkthrough.md
requires_bolts:
  - 031-multi-pose-vton-generation-ui
enables_bolts: []
requires_units: []
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 032-multi-pose-vton-generation-ui

## Overview

Implements the grouped pose set result view — the final piece letting a mayorista watch all selected poses complete and retry any failures.

## Objective

Mayorista sees live per-pose status after submitting a multi-pose generation, with a working retry action on any failed pose.

## Stories Included

- **003-pose-set-result-view**: Pose Set Grouped Result View (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Implementation plan for `PoseSetResultPage` — polling strategy, per-pose card layout → `implementation-plan.md`
- [ ] **2. Implement**: React components, polling against `GET /api/pose-sets/{id}`, retry wired to existing `005` batch item retry endpoint
- [ ] **3. Test**: Polling start/stop on terminal state, retry flow, unauthorized access handling → `test-walkthrough.md`

## Dependencies

### Requires
- 031-multi-pose-vton-generation-ui (redirects here after submit with a `pose_set_id`)
- 030-pose-set-service (`GET /api/pose-sets/{id}` must be available)

### Enables
- None (terminal bolt for this intent)

## Success Criteria

- [ ] Each selected pose renders as its own status card, updating live via polling
- [ ] Polling stops once all poses reach a terminal state
- [ ] Retry on a failed pose calls the existing `005` per-item retry endpoint and resumes polling
- [ ] Direct navigation to a `pose_set_id` not owned by the mayorista shows a 404 page

## Notes

Reuse the polling pattern already implemented in `002-batch-vton-generation-ui`'s `BatchProgressPage` (intent `005`) rather than building a new polling hook from scratch.

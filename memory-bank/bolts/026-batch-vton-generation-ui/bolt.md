---
id: 026-batch-vton-generation-ui
unit: 002-batch-vton-generation-ui
intent: 005-batch-vton-generation
type: simple-construction-bolt
status: complete
started: 2026-06-04T00:00:00Z
completed: 2026-06-04T00:00:00Z
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-06-04T00:00:00Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-06-04T00:00:00Z
    artifact: implementation-walkthrough.md
  - name: test
    completed: 2026-06-04T00:00:00Z
    artifact: test-walkthrough.md

requires_bolts: [025-batch-job-service]
enables_bolts: [027-batch-vton-generation-ui]
requires_units: [001-batch-job-service]
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 026-batch-vton-generation-ui

## Overview

Implements the two core UI pages: the batch creation wizard (garment + model pairing selection, submit) and the real-time batch progress monitoring page.

## Objective

Mayorista can create a batch through the UI and immediately see live per-item progress after submission.

## Stories Included

- **001-batch-creation-flow**: Batch Creation Flow (Must)
- **002-batch-progress-page**: Batch Progress Page (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Implementation plan for `BatchCreatePage` and `BatchProgressPage` → `implementation-plan.md`
- [ ] **2. Implement**: React components, API integration, 3s polling logic, routing
- [ ] **3. Test**: Interaction tests; polling start/stop; submit redirect → `test-walkthrough.md`

## Dependencies

### Requires
- 025-batch-job-service (POST /api/batches and GET /api/batches/{id} must be available)

### Enables
- 027-batch-vton-generation-ui (retry and history pages build on top of these)

## Success Criteria

- [ ] Mayorista can select 1–100 pairings and submit successfully
- [ ] Progress page auto-updates every 3s while batch is active
- [ ] Polling stops on terminal batch status
- [ ] Status badges visually distinguish all 4 states

## Notes

Reuse existing garment/model selection components from `003-vton-pipeline-ui` to keep UI consistent.

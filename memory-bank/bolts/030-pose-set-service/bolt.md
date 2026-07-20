---
id: 030-pose-set-service
unit: 002-pose-set-service
intent: 006-multi-pose-vton-generation
type: ddd-construction-bolt
status: complete
stories:
  - 001-submit-pose-set
  - 002-view-pose-set-results
created: 2026-07-17T00:00:00.000Z
started: 2026-07-18T06:47:24.000Z
completed: "2026-07-18T16:48:46Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-07-18T06:47:24.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-07-18T06:47:24.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-07-18T06:47:24.000Z
    artifact: adr-043-poseset-batch-atomicity.md, adr-044-batch-item-model-photo-reference.md, adr-045-tenant-aware-batch-contract.md
  - name: implement
    completed: 2026-07-18T06:47:24.000Z
    artifact: pose_set model, migration, repositories, services, schemas, routers, transaction-aware batch integration
requires_bolts:
  - 029-model-pose-service
enables_bolts:
  - 031-multi-pose-vton-generation-ui
requires_units:
  - 001-model-pose-service
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 030-pose-set-service

## Overview

Implements the `PoseSet` domain: expands a pose-aware submission into the existing `BatchJob`/`BatchItem` pipeline and exposes grouped result retrieval.

## Objective

Mayorista can submit a garment against a subset of a model's poses in one action and view all results grouped together, with zero new job-execution logic.

## Stories Included

- **001-submit-pose-set**: Submit Pose-Aware Generation and Register PoseSet (Must)
- **002-view-pose-set-results**: View Grouped Pose Set Results (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Define `PoseSet` entity, 1:1 relationship to `BatchJob` → `ddd-01-domain-model.md`
- [ ] **2. Technical Design**: `POST /api/pose-sets` (delegating to existing `create_batch`), `GET /api/pose-sets/{id}` (joining `BatchJob`/`BatchItem`/`ModelPhoto`), atomicity strategy → `ddd-02-technical-design.md`
- [ ] **3. Implement**: `PoseSet` model + migration, submission service delegating to `001-batch-job-service`'s existing `create_batch`, result aggregation service
- [ ] **4. Test**: Atomicity tests (no orphaned `PoseSet`), partial-completion status mapping, cross-mayorista access denial → `ddd-03-test-report.md`

## Dependencies

### Requires
- 029-model-pose-service (needs backfilled `Model`/`ModelPhoto` data to be consistent for all mayoristas)
- Note: Must reuse `001-batch-job-service`'s existing `create_batch` operation (intent `005-batch-vton-generation`) as-is — no duplication of `BatchJob`/`BatchItem` logic

### Enables
- 031-multi-pose-vton-generation-ui (needs both submission and retrieval APIs)

## Success Criteria

- [ ] `POST /api/pose-sets` creates `PoseSet` + `BatchJob`/`BatchItem`s atomically, response < 500ms
- [ ] Empty `pose_ids` rejected with 400, no records created
- [ ] `GET /api/pose-sets/{id}` correctly reflects partial completion per pose
- [ ] No orphaned `PoseSet` possible under any failure path

## Notes

This bolt must not modify `001-batch-job-service`'s domain logic — it calls into it. If `create_batch`'s current signature doesn't cleanly support internal (non-HTTP) invocation from another service, that's a technical-design decision to resolve in stage 2, not a reason to duplicate the logic.

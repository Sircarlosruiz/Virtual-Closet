---
id: 024-batch-job-service
unit: 001-batch-job-service
intent: 005-batch-vton-generation
type: ddd-construction-bolt
status: complete
started: 2026-06-04T00:00:00Z
completed: 2026-06-04T00:00:00Z
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-06-04T00:00:00Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-06-04T00:00:00Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-06-04T00:00:00Z
    artifact: adr-008-explicit-callback-vs-signals.md, adr-009-atomic-counter-updates.md
  - name: implement
    completed: 2026-06-04T00:00:00Z
    artifact: services/batch_completion_handler.py, services/batch_completion_handler_sync.py, services/batch_retry_service.py, api/routers/batches.py (retry endpoint), tasks/vton_task.py (callback), models/batch_job.py (retry_count), alembic migration update
  - name: test
    completed: 2026-06-04T00:00:00Z
    artifact: ddd-03-test-report.md

requires_bolts: [023-batch-job-service]
enables_bolts: [025-batch-job-service]
requires_units: []
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 024-batch-job-service

## Overview

Implements the Celery completion callbacks that drive per-item status updates, partial failure isolation, and the individual item retry endpoint.

## Objective

Close the feedback loop: when a `VtonJob` completes or fails, the corresponding `BatchItem` and `BatchJob` counters update correctly. Failures are isolated. Mayorista can retry individual failed items via `POST /api/batches/{id}/items/{item_id}/retry`.

## Stories Included

- **003-track-item-status**: Track Per-Item Status via Celery Callback (Must)
- **004-partial-failure-isolation**: Partial Failure Isolation (Must)
- **005-retry-failed-item**: Retry Failed Batch Item (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Status state machine for `BatchItem` and `BatchJob`; isolation invariants → `ddd-01-domain-model.md`
- [ ] **2. Technical Design**: Celery callback wiring, `F()` expression counter updates, retry endpoint design, idempotency strategy → `ddd-02-technical-design.md`
- [ ] **3. Implement**: Celery signal/callback, `on_vton_complete` / `on_vton_fail` handlers, retry ViewSet action
- [ ] **4. Test**: Concurrent update tests, partial failure scenarios, retry idempotency → `ddd-03-test-report.md`

## Dependencies

### Requires
- 023-batch-job-service (BatchJob + BatchItem models, VtonJob FK)

### Enables
- 025-batch-job-service (media save needs complete callback to exist)

## Success Criteria

- [ ] Concurrent counter updates don't lose increments (F() expressions used)
- [ ] 1 failed item in a 20-item batch doesn't affect remaining 19
- [ ] Retry re-enqueues item and resets status correctly
- [ ] 409 returned for retry on non-failed item

## Notes

Uncertainty is medium (2) due to Celery callback wiring — need to verify signal propagation from existing VtonJob task to new BatchItem handler without modifying core VTON task logic.

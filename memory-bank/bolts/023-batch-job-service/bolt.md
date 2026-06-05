---
id: 023-batch-job-service
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
    artifact: adr-005-transactional-celery-publish.md, adr-006-vtonjob-batch-item-fk.md, adr-007-sequential-celery-enqueue.md
  - name: implement
    completed: 2026-06-04T00:00:00Z
    artifact: models/batch_job.py, api/schemas/batches.py, repositories/batch_repo.py, services/batch_submission_service.py, api/routers/batches.py, alembic migration
  - name: test
    completed: 2026-06-04T00:00:00Z
    artifact: ddd-03-test-report.md

requires_bolts: []
enables_bolts: [024-batch-job-service]
requires_units: []
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 023-batch-job-service

## Overview

Establishes the core `BatchJob` domain — Django models, atomic submission endpoint, and Celery enqueue logic for all batch items.

## Objective

Implement `BatchJob` + `BatchItem` models and `POST /api/batches` so that a mayorista can submit a named batch of up to 100 VTON pairings in a single atomic operation.

## Stories Included

- **001-create-batch-job**: Create BatchJob and Persist Items (Must)
- **002-enqueue-batch-items**: Enqueue All Items as VtonJobs (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Define `BatchJob`, `BatchItem` entities, relationships, constraints → `ddd-01-domain-model.md`
- [ ] **2. Technical Design**: `POST /api/batches` endpoint, serializer validation, atomic transaction, Celery enqueue strategy → `ddd-02-technical-design.md`
- [ ] **3. Implement**: Django models, migrations, DRF ViewSet, Celery task delegation
- [ ] **4. Test**: Unit + integration tests; atomic rollback on enqueue failure → `ddd-03-test-report.md`

## Dependencies

### Requires
- None (foundational bolt for this intent)
- Note: Must coordinate with existing `VtonJob` model from `002-vton-job-service`

### Enables
- 024-batch-job-service (needs BatchJob + BatchItem models and VtonJob FK)

## Success Criteria

- [ ] `POST /api/batches` responds in < 500ms for 100 items
- [ ] Atomic rollback verified: no partial records on DB/Celery failure
- [ ] 100-item cap enforced with clear error message
- [ ] Mayorista scoping: only own garments/models can be batched

## Notes

Key design decision: `VtonJob` needs a new optional FK `batch_item_id` to support completion callbacks. This is a backwards-compatible schema change.

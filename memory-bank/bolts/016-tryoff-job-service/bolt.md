---
id: 016-tryoff-job-service
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
type: ddd-construction-bolt
status: complete
stories:
  - 001-submit-tryoff-job
  - 002-process-job-celery
  - 003-multi-garment-queue
created: 2026-05-31T00:00:00.000Z
started: 2026-05-31T15:00:00.000Z
completed: "2026-06-01T02:26:23Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-05-31T15:30:00.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-05-31T16:00:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-05-31T16:30:00.000Z
    artifact: adr-001-separate-celery-queue.md
  - name: implementation
    completed: 2026-05-31T17:00:00.000Z
    artifact: backend-code
  - name: testing
    completed: 2026-05-31T18:00:00.000Z
    artifact: ddd-03-test-report.md
requires_bolts:
  - 015-tryoff-model-service
enables_bolts:
  - 017-tryoff-job-service
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 3
  testing_scope: 3
---

# Bolt: 016-tryoff-job-service

## Overview

Core async job orchestration for garment extraction. Covers job creation API, Celery task that calls the model container, and multi-garment batch queuing from a single source image.

## Objective

Deliver the end-to-end happy path: mayorista submits one or more garment types → jobs are queued → Celery worker calls POST /tryoff on the model container → output is available. No media library save or retry yet (bolt 017).

## Stories Included

- **001-submit-tryoff-job**: POST /api/tryoff/jobs — create single job (Must)
- **002-process-job-celery**: Celery task — call model container, receive output PNG (Must)
- **003-multi-garment-queue**: POST /api/tryoff/jobs/batch — queue multiple garment types (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: TryoffJob entity; TryoffSession concept; garment_type enum; status transitions
- [ ] **2. Technical Design**: API contract (POST /jobs, POST /jobs/batch); Celery task design; model service call pattern; DB schema
- [ ] **3. Implementation**: FastAPI endpoints + Celery task + DB migration + model service httpx client
- [ ] **4. Test**: Integration test with real model container (or mock at TRYOFF_MODEL_URL); verify job status transitions

## Dependencies

### Requires
- 015-tryoff-model-service (model container must be healthy)

### Enables
- 017-tryoff-job-service (output handling, media library, retry)

## Success Criteria

- [ ] POST /api/tryoff/jobs creates a DB record and enqueues a Celery task
- [ ] POST /api/tryoff/jobs/batch creates N jobs for N garment types from same image
- [ ] Celery task completes end-to-end: receives PNG from model container
- [ ] Job status transitions: pending → processing → complete

## Notes

- Reuse existing Celery app instance from VTON pipeline
- Celery queue name: `tryoff` (separate from the VTON queue — confirmed in inception)
- `TRYOFF_MODEL_URL` env var for model container URL (default `http://tryoff-model-service:8003`)
- TryOff model runs on a **separate dedicated GPU node** — URL must reflect the correct host

---
id: 002-vton-job-service
unit: 002-vton-job-service
intent: 001-vton-generation-pipeline
type: ddd-construction-bolt
status: planned
stories:
  - 001-submit-vton-job
  - 002-process-job-celery
  - 003-poll-job-status
created: 2026-05-26T00:00:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts:
  - 001-media-service
enables_bolts:
  - 003-vton-job-service
  - 004-vton-pipeline-ui
requires_units: []
blocks: false

complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 3
---

# Bolt: 002-vton-job-service

## Overview

Implements the core VTON job lifecycle: job creation, RabbitMQ/Celery dispatch, async inference execution via the `VTONProvider` abstraction, and status polling. This is the highest-complexity bolt in the pipeline.

## Objective

Build the job submission endpoint, Celery worker task, and polling endpoint — covering the full path from `POST /api/vton/generate` → RabbitMQ → Celery → VTONProvider → MinIO → `completed` status visible via `GET /api/vton/jobs/{id}`.

## Stories Included

- **001-submit-vton-job**: Job submission with cloth type validation and RabbitMQ publish (Must)
- **002-process-job-celery**: Celery worker task — provider call, status transitions, result storage (Must)
- **003-poll-job-status**: Status polling endpoint with ownership enforcement and presigned result URL (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Define `VTONJob` aggregate, `ClothType` enum, `JobStatus` enum, state machine diagram → `ddd-01-domain-model.md`
- [ ] **2. Technical Design**: API routes, Celery task design, VTONProvider interface, RabbitMQ connection, DB schema → `ddd-02-technical-design.md`
- [ ] **3. Implement**: `models/vton_job.py`, `repositories/vton_job_repo.py`, `services/vton_job_service.py`, `tasks/vton_task.py`, `api/routers/vton.py`, `api/schemas/vton.py`, `services/providers/`
- [ ] **4. Test**: Integration tests for submit → process → complete flow; mock VTONProvider for unit tests → `ddd-03-test-report.md`

## Dependencies

### Requires
- 001-media-service (garment + model photo MinIO keys must exist)

### Enables
- 003-vton-job-service (retry logic + history — same service, next bolt)
- 004-vton-pipeline-ui (frontend calls these endpoints)

## Success Criteria

- [ ] Job submission returns `{ job_id, status: "queued" }` in < 500ms
- [ ] Celery worker processes job and transitions status correctly
- [ ] Poll endpoint returns correct status at each stage
- [ ] Ownership enforcement prevents cross-mayorista access
- [ ] VTONProvider interface tested with LocalGPUProvider (dev)
- [ ] Full lifecycle integration test passing

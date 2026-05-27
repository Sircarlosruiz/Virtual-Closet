---
id: 003-vton-job-service
unit: 002-vton-job-service
intent: 001-vton-generation-pipeline
type: ddd-construction-bolt
status: planned
stories:
  - 004-retry-on-failure
  - 005-job-history
created: 2026-05-26T00:00:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts:
  - 002-vton-job-service
enables_bolts:
  - 004-vton-pipeline-ui
requires_units: []
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 003-vton-job-service

## Overview

Extends the VTON job service with retry logic for transient provider failures and a paginated job history endpoint. Both features build on the `VTONJob` model and service layer established in bolt 002.

## Objective

Add exponential backoff retry to the Celery worker task and expose a paginated history endpoint. Retry configuration is environment-variable driven. History endpoint enforces mayorista-level isolation.

## Stories Included

- **004-retry-on-failure**: Auto-retry with exponential backoff on provider failure (Must)
- **005-job-history**: Paginated job history endpoint (Should)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Update `VTONJob` with `retry_count`, `max_retries`, `error_reason` fields; retry state transitions → `ddd-01-domain-model.md`
- [ ] **2. Technical Design**: Celery retry strategy (autoretry_for vs. manual), backoff formula, env var config, history query design → `ddd-02-technical-design.md`
- [ ] **3. Implement**: Update `tasks/vton_task.py` with retry logic; update `repositories/vton_job_repo.py` with `list_by_mayorista`; add `GET /api/vton/jobs` endpoint
- [ ] **4. Test**: Simulate provider failures, verify retry count increments, verify permanent failure after max_retries, test history pagination → `ddd-03-test-report.md`

## Dependencies

### Requires
- 002-vton-job-service (core job service must be complete)

### Enables
- 004-vton-pipeline-ui (history endpoint used by history page)

## Success Criteria

- [ ] Transient provider failure → job retried up to `VTON_MAX_RETRIES` times
- [ ] Exponential backoff delays verified in tests
- [ ] Non-retriable errors (4xx except 429) → immediately `failed`
- [ ] After max retries → `status=failed`, `error_reason` set
- [ ] History endpoint returns paginated, ownership-isolated results
- [ ] `retry_count` reflected in poll response

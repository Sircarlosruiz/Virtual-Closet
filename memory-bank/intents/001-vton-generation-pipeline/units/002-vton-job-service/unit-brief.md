---
unit: 002-vton-job-service
intent: 001-vton-generation-pipeline
phase: inception
status: complete
created: 2026-05-26T00:00:00.000Z
updated: 2026-05-26T00:00:00.000Z
---

# Unit Brief: 002-vton-job-service

## Purpose

Manages the full VTON job lifecycle: job submission, async dispatch via RabbitMQ/Celery, provider-agnostic inference execution, status tracking through all states, automatic retry on failure, result storage in MinIO, and job history retrieval.

## Scope

### In Scope
- VTON job creation and queueing (PostgreSQL + RabbitMQ)
- Cloth type validation (`upper_body`, `lower_body`, `dress`)
- Celery worker task: calls `VTONProvider`, updates job status at each transition
- Job status polling endpoint with result URL when complete
- Automatic retry with exponential backoff (configurable max retries)
- Result image storage in MinIO on completion
- Paginated job history for authenticated mayorista

### Out of Scope
- Photo uploads (handled by `001-media-service`)
- Provider implementation details beyond the `VTONProvider` interface
- Catalog creation from generated images (separate intent)
- Webhook/push notifications (polling only for MVP)
- Frontend UI (handled by `003-vton-pipeline-ui`)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-3 | Cloth type selection and validation | Must |
| FR-4 | Job submission — create record + publish to RabbitMQ | Must |
| FR-5 | Async Celery processing: call VTONProvider, update status | Must |
| FR-6 | Job status polling — return status + result_url | Must |
| FR-7 | Automatic retry on failure with exponential backoff | Must |
| FR-8 | Paginated job history for authenticated mayorista | Should |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `VTONJob` | A single generation request with full lifecycle tracking | id, mayorista_id, garment_photo_id, model_photo_id, cloth_type, status, retry_count, max_retries, error_reason, result_minio_key, created_at, started_at, completed_at |
| `ClothType` | Enum of supported garment categories | `upper_body`, `lower_body`, `dress` |
| `JobStatus` | Enum of possible job states | `queued`, `processing`, `completed`, `failed` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `submit_job` | Validates input, creates VTONJob, publishes Celery task | garment_photo_id, model_photo_id, cloth_type | `{ job_id, status: "queued" }` |
| `process_job` (Celery) | Calls VTONProvider, stores result, updates status | job_id | Updated VTONJob record |
| `get_job_status` | Returns current job status + result_url if complete | job_id, mayorista_id | VTONJob status DTO |
| `list_jobs` | Returns paginated job history for mayorista | mayorista_id, page, page_size | Paginated list of VTONJob |
| `retry_job` (internal) | Re-queues failed job if under retry limit | job_id | Updated VTONJob with retry_count++ |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 5 |
| Must Have | 4 |
| Should Have | 1 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-submit-vton-job | Submit VTON Job | Must | Planned |
| 002-process-job-celery | Process Job via Celery Worker | Must | Planned |
| 003-poll-job-status | Poll Job Status | Must | Planned |
| 004-retry-on-failure | Automatic Retry on Failure | Must | Planned |
| 005-job-history | Job History | Should | Planned |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| `001-media-service` | Needs garment and model photo MinIO keys to call VTONProvider |
| Auth (pre-condition) | Mayorista JWT required on all endpoints |

### Depended By
| Unit | Reason |
|------|--------|
| `003-vton-pipeline-ui` | Calls submit, poll, and history endpoints |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| RabbitMQ | Task queue for async job dispatch | Medium |
| Celery | Worker process for inference execution | Medium |
| VTONProvider (Replicate/LocalGPU) | AI inference | High |
| MinIO | Result image storage | Low |

---

## Technical Context

### Suggested Technology
- FastAPI routers: `api/routers/vton.py`
- Service: `services/vton_job_service.py`
- Celery task: `tasks/vton_task.py` (separate Celery app or registered in worker)
- Repository: `repositories/vton_job_repo.py`
- Model: `models/vton_job.py` (`VTONJob` SQLAlchemy model)
- Schema: `api/schemas/vton.py`
- Provider: `services/providers/vton_provider.py` (interface + implementations)

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| RabbitMQ | Task dispatch | AMQP via Celery |
| Celery workers | Async execution | Celery task |
| VTONProvider | AI inference | Provider interface |
| MinIO | Result storage | S3 API |
| PostgreSQL | Job state | SQLAlchemy async |

### Data Storage

| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| VTONJob records | PostgreSQL | Low-medium | Permanent |
| Generated images | MinIO | Medium (MB per image) | Permanent |

---

## Constraints

- `cloth_type` must be validated against the `ClothType` enum before job creation
- Retry count tracked in PostgreSQL — Celery workers must not store state in memory
- Max retries and backoff strategy configurable via environment variables
- Mayoristas can only access their own jobs (enforced in repository queries)
- `VTONProvider` interface must be used — no direct Replicate SDK calls in service layer

---

## Success Criteria

### Functional
- [ ] Job submitted → `{ job_id, status: "queued" }` returned in < 500ms
- [ ] Celery worker processes job and transitions to `completed` or `failed`
- [ ] Mayorista can poll status and get `result_url` when completed
- [ ] Failed jobs are retried up to max_retries with exponential backoff
- [ ] After max retries, job status is `failed` with error reason
- [ ] Mayorista can retrieve paginated job history

### Non-Functional
- [ ] Job submission p95 < 500ms
- [ ] Inference completion < 60s (dev), < 120s (prod)
- [ ] Permanent failure rate < 5%

### Quality
- [ ] Integration tests cover full job lifecycle (submit → process → complete)
- [ ] Retry logic tested with simulated provider failures

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| `002-vton-job-service` | ddd-construction-bolt | 001, 002, 003 | Domain model + job submission + Celery processing + polling |
| `003-vton-job-service` | ddd-construction-bolt | 004, 005 | Retry logic + job history |

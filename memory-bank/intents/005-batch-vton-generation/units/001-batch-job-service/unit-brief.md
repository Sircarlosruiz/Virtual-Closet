---
unit: 001-batch-job-service
intent: 005-batch-vton-generation
phase: inception
status: ready
unit_type: backend
default_bolt_type: ddd-construction-bolt
created: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
---

# Unit Brief: batch-job-service

## Purpose

Backend domain responsible for coordinating multi-item VTON batch jobs. Owns `BatchJob` and `BatchItem` entities, exposes the submission/status/retry API, enforces partial failure isolation, and triggers auto-save to the media library when items complete.

## Scope

### In Scope
- `BatchJob` aggregate and `BatchItem` entity (Django models)
- `POST /api/batches` — create batch and atomically enqueue all pairings
- `GET /api/batches/{id}` — batch status with per-item list
- `POST /api/batches/{id}/items/{item_id}/retry` — re-enqueue a failed item
- `GET /api/batches` — mayorista's batch history
- Celery signal/callback on individual `VtonJob` completion → update `BatchItem` status → save to media library
- Per-mayorista authorization (mayoristas can only access their own batches)

### Out of Scope
- Individual VTON job execution logic (handled by existing `002-vton-job-service`)
- Frontend UI (handled by `002-batch-vton-generation-ui`)
- New Celery queues or workers (reuses existing infrastructure)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-2 | Batch submission: create `BatchJob`, enqueue items, return `batch_id` in < 500ms | Must |
| FR-4 | Partial failure isolation: one job failure does not affect others | Must |
| FR-5 | Retry failed item: re-enqueue single item without creating a new batch | Must |
| FR-6 | Auto-save to media library on job completion, tagged with `batch_id` | Must |
| FR-7 | Batch history: list mayorista's batches with summary counts | Should |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `BatchJob` | Top-level record for a named group of VTON pairings | `id`, `mayorista_id`, `name`, `status` (pending/in-progress/complete/failed), `total_items`, `completed_count`, `failed_count`, `created_at`, `completed_at` |
| `BatchItem` | Individual pairing within a batch | `id`, `batch_id`, `garment_id`, `model_id`, `cloth_type`, `vton_job_id`, `status` (pending/processing/complete/failed), `error_message`, `result_media_id` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `create_batch` | Validate pairings, create `BatchJob` + `BatchItem` records, enqueue all as `VtonJob`s atomically | pairings list, batch name | `{ batch_id, total_items, status }` |
| `on_vton_job_complete` | Celery callback: update `BatchItem` status, save result to media library, update `BatchJob` counters | `vton_job_id`, result | updated `BatchItem`, media library entry |
| `on_vton_job_failed` | Celery callback: mark `BatchItem` failed with error message | `vton_job_id`, error | updated `BatchItem` |
| `retry_item` | Re-enqueue a failed `BatchItem` as a new `VtonJob`, reset item status | `batch_id`, `item_id` | updated `BatchItem` |
| `get_batch_status` | Fetch `BatchJob` + all `BatchItem` rows | `batch_id` | batch detail with per-item list |
| `list_batches` | Paginated list of mayorista's batches | mayorista JWT | batches with summary counts |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 7 |
| Must Have | 6 |
| Should Have | 1 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-create-batch-job | Create BatchJob and Persist Items | Must | Planned |
| 002-enqueue-batch-items | Enqueue All Items as VtonJobs | Must | Planned |
| 003-track-item-status | Track Per-Item Status via Celery Callback | Must | Planned |
| 004-partial-failure-isolation | Partial Failure Isolation | Must | Planned |
| 005-retry-failed-item | Retry Failed Batch Item | Must | Planned |
| 006-auto-save-to-media-library | Auto-Save Completed Item to Media Library | Must | Planned |
| 007-batch-history | Batch History API | Should | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `002-vton-job-service` (intent 001) | Delegates per-item VTON execution; must reuse `VtonJob` creation logic |

### Depended By

| Unit | Reason |
|------|--------|
| `002-batch-vton-generation-ui` | Consumes all REST endpoints exposed by this unit |

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| Celery / RabbitMQ | Async job enqueue and completion callbacks | Low — existing infra |
| MinIO / Media Library | Storing batch result images | Low — existing infra |

---

## Technical Context

### Suggested Technology
- Django model layer: `BatchJob`, `BatchItem` models in a new `batch_jobs` app
- Celery signals or task chaining to hook into existing `VtonJob` completion
- DRF serializers + ViewSets for the batch API endpoints

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| `VtonJob` creation | Internal service call | Python function call |
| Celery task result callback | Event | Celery task result / signal |
| Media Library save | Internal service call | Python function call |

### Data Storage

| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| `BatchJob` records | PostgreSQL | Low (< 1K/mayorista) | Permanent |
| `BatchItem` records | PostgreSQL | Medium (100× BatchJob volume) | Permanent |

---

## Constraints

- Batch item count hard cap: 100 (enforced in serializer validation)
- Batch submission must be atomic: either all `BatchItem` + `VtonJob` records are created, or none (use `transaction.atomic`)
- Must not modify existing `VtonJob` model or Celery task logic

---

## Success Criteria

### Functional
- [ ] `POST /api/batches` creates batch + enqueues all items within 500ms
- [ ] Failed `BatchItem` does not affect other items in same batch
- [ ] Retry endpoint re-enqueues a failed item and resets its status
- [ ] Completed item auto-appears in media library with `batch_id` tag
- [ ] `GET /api/batches` returns paginated batch list for authenticated mayorista only

### Non-Functional
- [ ] Submission API p95 < 500ms for 100-item batches
- [ ] No cross-mayorista data leakage in any endpoint

### Quality
- [ ] Code coverage > 80%
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 023-batch-job-service | ddd-construction-bolt | 001, 002 | Domain model + atomic batch submission |
| 024-batch-job-service | ddd-construction-bolt | 003, 004, 005 | Status tracking, failure isolation, retry |
| 025-batch-job-service | ddd-construction-bolt | 006, 007 | Media library integration + history API |

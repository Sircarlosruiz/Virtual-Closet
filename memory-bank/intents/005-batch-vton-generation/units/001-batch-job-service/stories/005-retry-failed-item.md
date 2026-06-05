---
id: 005-retry-failed-item
unit: 001-batch-job-service
intent: 005-batch-vton-generation
status: complete
priority: must
created: 2026-06-04T00:00:00Z
assigned_bolt: 024-batch-job-service
implemented: true
---

# Story: 005-retry-failed-item

## User Story

**As a** mayorista
**I want** to retry a single failed item in my batch
**So that** I can recover from transient failures without resubmitting the entire batch

## Acceptance Criteria

- [ ] **Given** a `BatchItem` with `status: failed`, **When** I call `POST /api/batches/{id}/items/{item_id}/retry`, **Then** a new `VtonJob` is created and enqueued for the same pairing and the `BatchItem.status` resets to `pending`
- [ ] **Given** a retry is requested on an item with `status: complete`, **When** the request is processed, **Then** a `409 Conflict` is returned — only failed items can be retried
- [ ] **Given** a retry is requested on an item with `status: processing`, **When** the request is processed, **Then** a `409 Conflict` is returned
- [ ] **Given** a batch owned by mayorista A, **When** mayorista B calls the retry endpoint, **Then** a `403 Forbidden` is returned
- [ ] **Given** a retry is enqueued, **When** `BatchJob` counters are checked, **Then** `failed_count` decrements by 1 and `BatchJob.status` transitions back to `in-progress` if it was `partial`/`failed`

## Technical Notes

- Create a new `VtonJob` for the retry (do not mutate the original)
- Update `BatchItem.vton_job_id` to the new job's ID
- `BatchJob.status` must re-evaluate after retry enqueue

## Dependencies

### Requires
- 003-track-item-status (status field must exist and be accurate)
- 004-partial-failure-isolation (BatchItem statuses are independent)

### Enables
- None directly; improves recovery path for mayorista

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Retry also fails | Item goes back to `failed`; mayorista can retry again |
| Multiple simultaneous retry calls for same item | Second call returns 409 (item already `pending`) |

## Out of Scope

- Automatic retry (already handled by existing VtonJob Celery retry logic — 3 attempts before permanent failure)

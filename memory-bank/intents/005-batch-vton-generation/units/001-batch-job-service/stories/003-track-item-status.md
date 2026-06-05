---
id: 003-track-item-status
unit: 001-batch-job-service
intent: 005-batch-vton-generation
status: complete
priority: must
created: 2026-06-04T00:00:00Z
assigned_bolt: 024-batch-job-service
implemented: true
---

# Story: 003-track-item-status

## User Story

**As a** mayorista
**I want** to see the real-time status of every item in my batch
**So that** I know which jobs are done, in progress, or failed at a glance

## Acceptance Criteria

- [ ] **Given** a `VtonJob` transitions to `in-progress`, **When** the Celery task starts, **Then** the corresponding `BatchItem.status` updates to `processing`
- [ ] **Given** a `VtonJob` completes successfully, **When** the task finishes, **Then** `BatchItem.status` updates to `complete` and `BatchJob.completed_count` increments by 1
- [ ] **Given** a `VtonJob` fails permanently (retries exhausted), **When** failure is confirmed, **Then** `BatchItem.status` updates to `failed` with `error_message` set and `BatchJob.failed_count` increments by 1
- [ ] **Given** all `BatchItem`s reach a terminal state, **When** the last one completes/fails, **Then** `BatchJob.status` transitions to `complete` (all success) or `partial` (mixed)
- [ ] **Given** `GET /api/batches/{id}`, **When** called by the batch owner, **Then** response includes `{ batch_id, status, total_items, completed_count, failed_count, items: [{item_id, status, error_message, result_media_id}] }`

## Technical Notes

- Implement via Celery task signal or a dedicated `on_vton_job_result` Celery chord/callback
- `BatchJob.status` computed on each item terminal transition; avoid race conditions with `F()` expressions for counter increments
- Status transitions are append-only; no status can regress

## Dependencies

### Requires
- 002-enqueue-batch-items (VtonJob IDs must be linked to BatchItems)

### Enables
- 004-partial-failure-isolation
- 005-retry-failed-item

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Concurrent status updates for same batch | Use `F('completed_count') + 1` to avoid lost updates |
| Status endpoint called by different mayorista | 403 Forbidden |

## Out of Scope

- Media library save (Story 006)
- Retry logic (Story 005)

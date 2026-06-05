---
id: 002-enqueue-batch-items
unit: 001-batch-job-service
intent: 005-batch-vton-generation
status: complete
priority: must
created: 2026-06-04T00:00:00Z
assigned_bolt: 023-batch-job-service
implemented: true
---

# Story: 002-enqueue-batch-items

## User Story

**As a** system
**I want** to enqueue every pairing in a new batch as individual VTON jobs atomically
**So that** all items start processing immediately after batch creation

## Acceptance Criteria

- [ ] **Given** a `BatchJob` is created with N items, **When** the batch is submitted, **Then** N individual `VtonJob` records are created and enqueued to Celery within the same atomic transaction
- [ ] **Given** all N `VtonJob`s are enqueued, **When** the `BatchJob` is read, **Then** its `status` is `in-progress`
- [ ] **Given** enqueueing fails for any item, **When** the exception occurs, **Then** the entire transaction is rolled back — no `BatchJob`, `BatchItem`, or `VtonJob` records are persisted
- [ ] **Given** a batch of 100 items, **When** all jobs are enqueued, **Then** the total enqueue time remains within the 500ms API response budget

## Technical Notes

- Reuse existing `VtonJob` creation logic from `002-vton-job-service`; do not duplicate task definitions
- Each `BatchItem.vton_job_id` is set to the corresponding `VtonJob.id` at creation time
- `BatchJob.status` transitions to `in-progress` immediately after successful enqueue
- Use `VtonJob.batch_item_id` (new FK) to link back to `BatchItem` for completion callbacks

## Dependencies

### Requires
- 001-create-batch-job (BatchJob and BatchItem records must exist)

### Enables
- 003-track-item-status (VtonJob IDs are set on BatchItems)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Celery broker temporarily unavailable | Transaction rolled back; 503 returned to client |
| VtonJob creation raises ValidationError | Entire batch transaction rolled back; specific item error returned |

## Out of Scope

- VTON inference execution (handled by existing Celery worker)
- Per-item status updates (Story 003)

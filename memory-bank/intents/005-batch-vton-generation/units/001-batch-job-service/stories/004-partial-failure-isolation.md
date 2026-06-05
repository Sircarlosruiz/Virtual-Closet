---
id: 004-partial-failure-isolation
unit: 001-batch-job-service
intent: 005-batch-vton-generation
status: complete
priority: must
created: 2026-06-04T00:00:00Z
assigned_bolt: 024-batch-job-service
implemented: true
---

# Story: 004-partial-failure-isolation

## User Story

**As a** mayorista
**I want** failed items in my batch to not affect the other items
**So that** I get as many results as possible even if some jobs fail

## Acceptance Criteria

- [ ] **Given** item #3 of a 10-item batch fails permanently, **When** the failure is registered, **Then** items #1–2 and #4–10 continue processing unaffected
- [ ] **Given** 3 out of 20 items fail, **When** all 17 successful items complete, **Then** they appear in the media library without waiting for the 3 failed items to resolve
- [ ] **Given** a batch has both successful and failed items, **When** all items reach terminal state, **Then** `BatchJob.status` is `partial` (not `failed`)
- [ ] **Given** ALL items fail, **When** the last one fails, **Then** `BatchJob.status` is `failed`
- [ ] **Given** ALL items succeed, **When** the last one completes, **Then** `BatchJob.status` is `complete`

## Technical Notes

- Each `BatchItem` is an independent Celery task — failure of one does not raise in others
- `BatchJob.status` is computed, not stored as a Celery group result
- Use `ignore_result=False` on individual tasks to ensure failure signals propagate to the callback

## Dependencies

### Requires
- 003-track-item-status (status update logic must exist)

### Enables
- 006-auto-save-to-media-library (successful items proceed regardless of others)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Celery worker crash mid-batch | Surviving tasks continue; crashed task marked failed after visibility timeout |
| Batch with 1 item that fails | BatchJob.status = `failed` |

## Out of Scope

- Retry logic (Story 005) — this story only covers isolation, not recovery

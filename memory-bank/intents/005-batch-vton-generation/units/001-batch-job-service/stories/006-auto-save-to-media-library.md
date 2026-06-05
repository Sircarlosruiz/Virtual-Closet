---
id: 006-auto-save-to-media-library
unit: 001-batch-job-service
intent: 005-batch-vton-generation
status: complete
priority: must
created: 2026-06-04T00:00:00Z
assigned_bolt: 025-batch-job-service
implemented: true
---

# Story: 006-auto-save-to-media-library

## User Story

**As a** mayorista
**I want** completed batch items to appear in my media library automatically
**So that** I can use results immediately without any manual action

## Acceptance Criteria

- [ ] **Given** a `BatchItem` transitions to `complete`, **When** the Celery callback fires, **Then** the result image is saved to the mayorista's media library within 5 seconds
- [ ] **Given** the media item is saved, **When** it appears in the library, **Then** its metadata includes `batch_id`, `batch_name`, `garment_id`, and `model_id`
- [ ] **Given** the media save fails (MinIO error), **When** the error occurs, **Then** the `BatchItem.status` remains `complete` but a `media_save_error` flag is set — the item is not marked as failed
- [ ] **Given** a batch with 20 successful items, **When** all complete, **Then** all 20 appear in the media library with correct `batch_id` tagging
- [ ] **Given** I browse my media library filtered by `batch_id`, **When** the filter is applied, **Then** only items from that batch are shown

## Technical Notes

- Reuse existing media library save logic from `005-media-library-save` (intent 004, unit 002)
- Add `batch_id` and `batch_name` to the media item's metadata dict at save time
- Media save is triggered in the Celery task completion callback, not in the HTTP request path

## Dependencies

### Requires
- 003-track-item-status (completion callback must exist)
- 004-partial-failure-isolation (successful items proceed independently)

### Enables
- None; this is a terminal action for successful items

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| MinIO temporarily unavailable | Media save retried up to 3× via Celery retry; `media_save_error` flag set if all retries fail |
| Same result saved twice (duplicate callback) | Idempotency check on `vton_job_id` prevents duplicate media entries |

## Out of Scope

- Manual "add to catalog" action — that is handled by the existing catalog management feature

---
id: 002-view-pose-set-results
unit: 002-pose-set-service
intent: 006-multi-pose-vton-generation
status: complete
priority: must
created: 2026-07-17T00:00:00.000Z
assigned_bolt: 030-pose-set-service
implemented: true
---

# Story: 002-view-pose-set-results

## User Story

**As a** mayorista
**I want** to see all the poses of a submission grouped together with their individual status
**So that** I can tell at a glance which angles are done, still processing, or failed

## Acceptance Criteria

- [ ] **Given** I own the `PoseSet`, **When** I `GET /api/pose-sets/{pose_set_id}`, **Then** I receive `{pose_set_id, garment_id, model_id, status, items: [{pose_type, batch_item_id, media_id, image_url, status}]}` where `status` is derived from the underlying `BatchJob` status (`pending/in-progress/complete/partial/failed`)
- [ ] **Given** some poses are complete and others are still pending, **When** I fetch the pose set, **Then** each item's `status` reflects its own `BatchItem` state independently (partial completion is visible per item, not just at the set level)
- [ ] **Given** the `PoseSet` doesn't exist or isn't mine, **When** I request it, **Then** a `404` is returned
- [ ] **Given** a pose's `BatchItem` failed, **When** I fetch the pose set, **Then** that item's entry includes the error reason (mirroring existing `BatchItem.error_message`)

## Technical Notes

- Join `PoseSet` → `BatchJob` → `BatchItem` (existing tables from `005`), map each `BatchItem.model_id` back to its `pose` type via `001-model-pose-service`'s `ModelPhoto`
- No new polling infrastructure — same read-heavy GET pattern as existing `GET /api/batches/{id}`

## Dependencies

### Requires
- 001-submit-pose-set (a `PoseSet` must exist to view)

### Enables
- `003-multi-pose-vton-generation-ui` pose set result view

## Edge Cases

| Scenario | Expected Behavior |
|----------|--------------------|
| All poses still pending | `status: "pending"`, all items show `pending` |
| One pose fails, rest complete | Set `status: "partial"` (mirrors `BatchJob` partial state), failed item shows error message |
| Client retries a failed item via existing `005` retry endpoint | Next `GET /api/pose-sets/{id}` reflects the item's updated status automatically (no pose-set-specific retry logic needed) |

## Out of Scope

- A dedicated retry endpoint scoped to pose sets (reuses `005`'s existing per-item retry as-is)

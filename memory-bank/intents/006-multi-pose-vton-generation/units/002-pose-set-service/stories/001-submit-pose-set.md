---
id: 001-submit-pose-set
unit: 002-pose-set-service
intent: 006-multi-pose-vton-generation
status: complete
priority: must
created: 2026-07-17T00:00:00.000Z
assigned_bolt: 030-pose-set-service
implemented: true
---

# Story: 001-submit-pose-set

## User Story

**As a** mayorista
**I want** to submit one garment against a subset of my model's poses in a single action
**So that** I get a matching try-on image for each selected angle without submitting them one at a time

## Acceptance Criteria

- [ ] **Given** I own the `garment_id` and `model_id`, **When** I `POST /api/pose-sets` with `{garment_id, model_id, cloth_type, pose_ids[]}` where `pose_ids` is a non-empty subset of the model's poses, **Then** a `BatchJob` is created with `total_items` equal to `len(pose_ids)`, one `BatchItem` per selected pose (`model_id` on each item pointing to that pose's `ModelPhoto`), and a `PoseSet` is created linking `{mayorista_id, model_id, garment_id, batch_id}` — all in one atomic transaction
- [ ] **Given** the response is returned, **When** submission succeeds, **Then** it includes `{pose_set_id, batch_id, total_items}` within 500ms
- [ ] **Given** `pose_ids` is empty, **When** I submit, **Then** a `400` error is returned (`"At least one pose must be selected"`)
- [ ] **Given** any id in `pose_ids` doesn't belong to the specified `model_id`, **When** I submit, **Then** a `400` error is returned and no `BatchJob`/`PoseSet` is created
- [ ] **Given** the underlying batch creation fails for any reason, **When** the error occurs, **Then** no partial `PoseSet` or `BatchJob`/`BatchItem` records are persisted

## Technical Notes

- Delegates pairing construction + `BatchJob`/`BatchItem` persistence to `001-batch-job-service`'s existing `create_batch` operation (intent `005`) — do not duplicate that logic
- Wrap the call to `create_batch` and the `PoseSet` insert in the same `transaction.atomic()` block
- A model with exactly 1 pose and `pose_ids=[that pose]` behaves identically to a manual single-pairing batch submission

## Dependencies

### Requires
- `001-model-pose-service` stories 001–003 (Model + poses must exist and be listable)
- `001-batch-job-service` (existing, intent `005`) `create_batch` operation

### Enables
- 002-view-pose-set-results

## Edge Cases

| Scenario | Expected Behavior |
|----------|--------------------|
| Model has only 1 pose, all selected | `total_items=1`, functionally identical to a regular single-item batch |
| Garment belongs to a different mayorista | `403`/`404`, same as existing batch validation |
| `pose_ids` contains duplicates | Deduplicated before building pairings, or `400` — Construction to decide, document choice in code |

## Out of Scope

- Grouped result retrieval (Story 002)
- Retry of a failed pose (reuses existing `005` per-item retry endpoint, no new work)

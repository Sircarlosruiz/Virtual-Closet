---
id: 003-list-model-poses
unit: 001-model-pose-service
intent: 006-multi-pose-vton-generation
status: complete
priority: must
created: 2026-07-17T00:00:00.000Z
assigned_bolt: 028-model-pose-service
implemented: true
---

# Story: 003-list-model-poses

## User Story

**As a** mayorista
**I want** to list all pose photos registered for one of my models
**So that** I can review what's uploaded and pick this model for a multi-pose generation

## Acceptance Criteria

- [ ] **Given** I own the target `Model`, **When** I `GET /api/models/{model_id}/poses`, **Then** I receive a list of `{id, pose, image_url, uploaded_at}` for every pose on that model, ordered deterministically (`front`, `side`, `back`)
- [ ] **Given** the `Model` doesn't exist or isn't mine, **When** I request its poses, **Then** a `404` is returned
- [ ] **Given** the `Model` has zero poses (should not normally happen post-creation), **When** I list its poses, **Then** an empty list is returned without error

## Technical Notes

- `image_url` is a presigned URL (15-min TTL), same convention as existing media endpoints

## Dependencies

### Requires
- 001-create-model
- 002-upload-pose-photo

### Enables
- `003-multi-pose-vton-generation-ui` model/pose management page
- `002-pose-set-service` (validates `pose_ids` against this list)

## Edge Cases

| Scenario | Expected Behavior |
|----------|--------------------|
| Presigned URL expired by the time client uses it | Client re-fetches the list to get a fresh URL |
| Model owned by another mayorista | `404`, not `403` (avoid leaking existence) |

## Out of Scope

- Pagination (max 3 poses per model, list is always small)

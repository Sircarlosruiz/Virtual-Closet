---
id: 002-upload-pose-photo
unit: 001-model-pose-service
intent: 006-multi-pose-vton-generation
status: complete
priority: must
created: 2026-07-17T00:00:00.000Z
assigned_bolt: 028-model-pose-service
implemented: true
---

# Story: 002-upload-pose-photo

## User Story

**As a** mayorista
**I want** to upload a photo of my model tagged with a specific pose type
**So that** I can build up a multi-angle set (front/side/back) for that model

## Acceptance Criteria

- [ ] **Given** I own the target `Model`, **When** I `POST /api/models/{model_id}/poses` with a valid JPG/PNG (≤10MB) and `pose` in `{front, side, back}`, **Then** a `ModelPhoto` is created linked to the `Model` with that pose type, stored in MinIO under my mayorista namespace, and a presigned URL (15-min TTL) is returned
- [ ] **Given** the `Model` already has a pose photo of the requested `pose` type, **When** I try to upload another with the same type, **Then** a `400` error is returned (`"Pose type already exists for this model"`)
- [ ] **Given** I upload a file that isn't JPG/PNG or exceeds 10MB, **When** the request is processed, **Then** it is rejected per existing `001-media-service` validation rules
- [ ] **Given** I don't own the target `Model`, **When** I attempt to upload a pose to it, **Then** a `403`/`404` is returned

## Technical Notes

- Reuse `services/media_service.py` file validation and MinIO write logic from `001-media-service`
- `pose` is a Django `TextChoices`/enum field: `front`, `side`, `back`
- Enforce "at most 3 poses per model" implicitly via the enum's 3 values + the duplicate-type check

## Dependencies

### Requires
- 001-create-model (needs a `Model` to attach to)

### Enables
- 003-list-model-poses
- `002-pose-set-service` submission stories (need at least 1 pose to exist)

## Edge Cases

| Scenario | Expected Behavior |
|----------|--------------------|
| First pose uploaded to a fresh `Model` | Succeeds regardless of which pose type is chosen first |
| Concurrent uploads of the same pose type | Second request fails the duplicate check (DB unique constraint on `(model_id, pose)`) |
| `pose` value outside the enum | `400` validation error |

## Out of Scope

- Replacing/deleting an existing pose photo (not required by any FR in this intent)

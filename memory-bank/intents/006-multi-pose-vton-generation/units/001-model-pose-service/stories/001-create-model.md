---
id: 001-create-model
unit: 001-model-pose-service
intent: 006-multi-pose-vton-generation
status: complete
priority: must
created: 2026-07-17T00:00:00.000Z
assigned_bolt: 028-model-pose-service
implemented: true
---

# Story: 001-create-model

## User Story

**As a** mayorista
**I want** to create a named `Model` identity
**So that** I can group multiple pose photos of the same model together instead of uploading unrelated single photos

## Acceptance Criteria

- [ ] **Given** I am authenticated, **When** I `POST /api/models` with `{name}`, **Then** a `Model` record is created with `{id, mayorista_id, name, created_at}` and `name` is required (non-empty)
- [ ] **Given** I create a `Model`, **When** it is persisted, **Then** it has zero poses initially and is not usable in a submission until at least 1 pose is uploaded (enforced by `002-upload-pose-photo` and `002-pose-set-service`)
- [ ] **Given** I omit `name`, **When** I submit the request, **Then** a `400` error is returned

## Technical Notes

- New `Model` Django model, same app as `ModelPhoto`
- `mayorista_id` comes from the authenticated JWT session, same pattern as existing `001-media-service`

## Dependencies

### Requires
- None (foundational story)

### Enables
- 002-upload-pose-photo (needs a `Model` to attach poses to)
- 003-list-model-poses

## Edge Cases

| Scenario | Expected Behavior |
|----------|--------------------|
| Duplicate model name for same mayorista | Allowed — names are not unique keys, `id` is |
| Very long name (255+ chars) | `400` validation error |

## Out of Scope

- Pose photo upload (Story 002)
- Editing/deleting a model (not required by any FR in this intent)

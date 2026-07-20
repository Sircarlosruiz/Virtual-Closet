---
id: 001-model-pose-management-ui
unit: 003-multi-pose-vton-generation-ui
intent: 006-multi-pose-vton-generation
status: complete
priority: must
created: 2026-07-17T00:00:00.000Z
assigned_bolt: 031-multi-pose-vton-generation-ui
implemented: true
---

# Story: 001-model-pose-management-ui

## User Story

**As a** mayorista
**I want** a page to create a model and upload its pose photos
**So that** I can build a multi-angle model before using it in generation

## Acceptance Criteria

- [ ] **Given** I navigate to the model management page, **When** it loads, **Then** I see my existing models with their pose count (e.g., "María — 2/3 poses")
- [ ] **Given** I click "New Model", **When** I enter a name and confirm, **Then** a `Model` is created via `POST /api/models` and I land on its pose upload view
- [ ] **Given** I'm on a model's pose upload view, **When** I upload a photo, **Then** I pick a pose type from `front`/`side`/`back` restricted to types not yet used on this model, and it's submitted via `POST /api/models/{model_id}/poses`
- [ ] **Given** a model already has all 3 pose types filled, **When** I view its upload view, **Then** no more pose types are offered and the model is shown as "complete"
- [ ] **Given** a legacy single-pose model (created via backfill), **When** I view it in this page, **Then** it shows correctly with its 1 pose (`front`) and I can add `side`/`back` to it like any other model

## Technical Notes

- Reuse existing photo upload component/validation UX from `001-media-service`'s model upload flow
- Pose type selector should visually disable already-used types

## Dependencies

### Requires
- `001-model-pose-service` stories 001–003 (API must be deployed) — cross-unit dependency

### Enables
- 002-pose-selection-submission-ui (needs models with poses to select from)

## Edge Cases

| Scenario | Expected Behavior |
|----------|--------------------|
| Upload fails validation (wrong type/size) | Inline error shown, upload view stays open |
| Model has 0 poses (transient state right after creation) | Shown as "incomplete", cannot yet be used for generation |

## Out of Scope

- Editing/replacing an existing pose photo
- Deleting a model

---
id: 002-pose-selection-submission-ui
unit: 003-multi-pose-vton-generation-ui
intent: 006-multi-pose-vton-generation
status: complete
priority: must
created: 2026-07-17T00:00:00.000Z
assigned_bolt: 031-multi-pose-vton-generation-ui
implemented: true
---

# Story: 002-pose-selection-submission-ui

## User Story

**As a** mayorista
**I want** to pick a garment and model, see all of that model's poses pre-selected, and deselect the ones I don't want
**So that** I control exactly which angles get generated before submitting

## Acceptance Criteria

- [ ] **Given** I select a garment and a multi-pose model, **When** the model has more than 1 pose, **Then** all of its poses are shown as checkboxes, pre-selected by default
- [ ] **Given** at least 1 pose is selected, **When** I view the submit action, **Then** it's enabled and shows the count (e.g., "Generate 3 Poses")
- [ ] **Given** I deselect poses down to 0 selected, **When** I view the submit action, **Then** it's disabled
- [ ] **Given** I submit with N poses selected, **When** the API responds, **Then** I'm redirected to the pose set result view (`003-pose-set-result-view`) using the returned `pose_set_id`
- [ ] **Given** I select a model with exactly 1 pose (including legacy backfilled models), **When** the selection UI renders, **Then** no pose-selection step is shown — the flow behaves exactly like today's single-pairing submission

## Technical Notes

- POST body: `{garment_id, model_id, cloth_type, pose_ids: [...]}` to `002-pose-set-service`'s `POST /api/pose-sets`
- Reuse existing garment/cloth-type selector components from `003-vton-pipeline-ui` / `002-batch-vton-generation-ui`

## Dependencies

### Requires
- `001-model-pose-service` (poses to select from), `002-pose-set-service` (submission API) — cross-unit dependencies
- 001-model-pose-management-ui (models must exist with poses)

### Enables
- 003-pose-set-result-view

## Edge Cases

| Scenario | Expected Behavior |
|----------|--------------------|
| Model has 0 poses (shouldn't happen post-creation, but defensive) | Model excluded from the picker or shown disabled with a tooltip |
| API returns 400 (empty pose_ids somehow bypassed client validation) | Inline error toast, form stays open |
| API returns 500 | Inline error toast, form stays open |

## Out of Scope

- The pose set result view itself (Story 003)

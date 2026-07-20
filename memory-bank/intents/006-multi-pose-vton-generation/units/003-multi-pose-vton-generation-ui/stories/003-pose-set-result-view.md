---
id: 003-pose-set-result-view
unit: 003-multi-pose-vton-generation-ui
intent: 006-multi-pose-vton-generation
status: complete
priority: must
created: 2026-07-17T00:00:00.000Z
assigned_bolt: 032-multi-pose-vton-generation-ui
implemented: true
---

# Story: 003-pose-set-result-view

## User Story

**As a** mayorista
**I want** to see all the poses from one submission grouped together with live status
**So that** I can review the full multi-angle set as it completes and retry any that failed

## Acceptance Criteria

- [ ] **Given** I land on the pose set result view after submitting, **When** the page loads, **Then** it polls `GET /api/pose-sets/{pose_set_id}` and shows one card per selected pose (labeled `front`/`side`/`back`) with its current status
- [ ] **Given** a pose is still processing, **When** I view its card, **Then** it shows a pending/processing indicator
- [ ] **Given** a pose completes, **When** the next poll returns, **Then** its card updates to show the generated image
- [ ] **Given** a pose fails, **When** I view its card, **Then** it shows the error reason and a "Retry" button that calls the existing batch item retry endpoint (`005-batch-vton-generation`)
- [ ] **Given** all poses reach a terminal state (complete or failed), **When** the last poll confirms this, **Then** polling stops

## Technical Notes

- Reuse the polling pattern from `002-batch-vton-generation-ui`'s `BatchProgressPage`
- Retry calls existing `POST /api/batches/{batch_id}/items/{item_id}/retry` directly (via `batch_item_id` returned in the pose set payload) — no new retry endpoint

## Dependencies

### Requires
- `002-pose-set-service` story 002 (result retrieval API) — cross-unit dependency
- 002-pose-selection-submission-ui (redirects here with `pose_set_id`)

### Enables
- None (terminal story in this unit)

## Edge Cases

| Scenario | Expected Behavior |
|----------|--------------------|
| Direct navigation to a `pose_set_id` I don't own | 404 page shown |
| Retry succeeds | Item's card returns to pending/processing on next poll |
| Network error during polling | Retry poll silently, show a subtle "reconnecting" indicator, don't blow away last known state |

## Out of Scope

- Adding pose set results directly to a catalog (deferred — open question in requirements.md)

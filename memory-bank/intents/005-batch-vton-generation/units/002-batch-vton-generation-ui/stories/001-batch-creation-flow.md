---
id: 001-batch-creation-flow
unit: 002-batch-vton-generation-ui
intent: 005-batch-vton-generation
status: complete
priority: must
created: 2026-06-04T00:00:00Z
assigned_bolt: 026-batch-vton-generation-ui
implemented: true
---

# Story: 001-batch-creation-flow

## User Story

**As a** mayorista
**I want** to select multiple garment+model pairings through a UI and submit them as a batch
**So that** I can generate many VTON results in one action without repeating individual job submissions

## Acceptance Criteria

- [ ] **Given** I navigate to the "New Batch" page, **When** the page loads, **Then** I see a garment selection grid from my media library
- [ ] **Given** the garment selection grid, **When** I select garments (up to 100), **Then** each selected garment shows a pairing row where I can pick a model photo and cloth type
- [ ] **Given** I have at least 1 pairing configured, **When** I view the submission area, **Then** a "Submit Batch" button is enabled and shows the pairing count (e.g., "Submit 15 Jobs")
- [ ] **Given** I have 0 pairings configured, **When** I view the submission area, **Then** the "Submit Batch" button is disabled
- [ ] **Given** I submit the batch, **When** the API responds with `batch_id`, **Then** I am redirected to the `BatchProgressPage` for that batch
- [ ] **Given** I optionally enter a batch name, **When** I submit, **Then** the name is sent with the request and shown on the progress page

## Technical Notes

- Reuse existing garment/model thumbnail components from `003-vton-pipeline-ui`
- Cloth type selector: `upper-body`, `lower-body`, `dresses` (same options as single VTON job)
- Show live count indicator: "X pairings selected"
- POST body: `{ name, items: [{ garment_id, model_id, cloth_type }] }`

## Dependencies

### Requires
- 001-batch-job-service stories (API must be deployed) — cross-unit dependency

### Enables
- 002-batch-progress-page (redirect after submit)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Select 101 garments | 101st garment checkbox disabled; tooltip "Maximum 100 items per batch" |
| Model library is empty | Show prompt to upload model photos |
| API returns 500 | Show inline error toast; batch creation form stays open |

## Out of Scope

- Editing a submitted batch
- Saving a draft batch

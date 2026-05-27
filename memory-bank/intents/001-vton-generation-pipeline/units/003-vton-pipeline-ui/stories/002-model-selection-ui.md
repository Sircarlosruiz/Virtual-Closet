---
id: 002-model-selection-ui
unit: 003-vton-pipeline-ui
intent: 001-vton-generation-pipeline
status: draft
priority: must
created: 2026-05-26T00:00:00Z
assigned_bolt: 004-vton-pipeline-ui
implemented: false
---

# Story: 002-model-selection-ui

## User Story

**As a** mayorista
**I want** to choose a model photo from my own uploads or from the curated library
**So that** the VTON generation uses the right person

## Acceptance Criteria

- [ ] **Given** I am on the generate page, **When** I open the model selector, **Then** I see two tabs: "My Models" and "Model Library"
- [ ] **Given** I am on "My Models" tab, **When** it loads, **Then** my uploaded model photos are shown as a grid of thumbnails fetched from `GET /api/media/models/mine`
- [ ] **Given** I am on "My Models" tab, **When** I have no uploads, **Then** I see an upload prompt + "Upload your own model" button
- [ ] **Given** I click "Upload your own model", **When** I select a valid file, **Then** the file is uploaded via `POST /api/media/models` and appears immediately in the grid
- [ ] **Given** I am on "Model Library" tab, **When** it loads, **Then** the curated model photos are shown from `GET /api/media/models/curated`
- [ ] **Given** I click a model thumbnail (either tab), **When** it is selected, **Then** it shows a selected state (ring/checkmark) and the model_photo_id is stored in form state
- [ ] **Given** a model is selected, **When** I navigate to the next step, **Then** the selection is preserved

## Technical Notes

- Component: `ModelSelector` with internal `Tabs` (shadcn/ui)
- Thumbnails: use presigned URLs from API response
- Upload within "My Models" tab reuses the same upload component as garment (but hits `/api/media/models`)
- Grid: 2 columns mobile, 3-4 columns desktop
- Selected state: Tailwind ring-2 + checkmark overlay

## Dependencies

### Requires
- `001-garment-upload-ui` (appears after garment is uploaded in the flow)

### Enables
- `003-vton-pipeline-ui/003-job-submission-ui`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Curated library empty | Show placeholder message in "Model Library" tab |
| Model upload fails | Inline error, stays on "My Models" tab |
| Switching tabs resets selection | No — selection persists across tab switches |

## Out of Scope

- Deleting model photos from within this UI
- Filtering or searching models

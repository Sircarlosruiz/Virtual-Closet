---
id: 002-garment-type-selector
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 019-tryoff-pipeline-ui
implemented: false
---

# Story: 002-garment-type-selector

## User Story

**As a** mayorista
**I want** to select which garments to extract from my source image
**So that** I can get separate images for the top and pants in one session

## Acceptance Criteria

- [ ] **Given** a source image has been selected, **When** the garment selector appears, **Then** I see three toggleable chips: "Upper Garment", "Lower Garment", "Full Dress/Outfit"
- [ ] **Given** the chips are shown, **When** I click multiple chips, **Then** all selected chips are visually highlighted (multi-select allowed)
- [ ] **Given** I have selected at least one garment type, **When** I click "Start Extraction", **Then** POST /api/tryoff/jobs/batch is called with the selected types and the source image
- [ ] **Given** no garment type is selected, **When** I click "Start Extraction", **Then** the button is disabled and a tooltip says "Select at least one garment type"
- [ ] **Given** the batch request is submitted, **When** the response arrives, **Then** I am navigated to the extraction status page showing all queued jobs

## Technical Notes

- Chip values map to API values: `upper` / `lower` / `dress`
- Chip labels shown to user: "Upper Garment" / "Lower Garment" / "Full Dress / Outfit"
- State: `selectedTypes: Set<string>` managed with `useState`
- Submit calls `POST /api/tryoff/jobs/batch` with `{ source_image_id, garment_types: [...selectedTypes] }`
- On success: `router.push("/tryoff/status?session_image_id=<source_image_id>")`
- shadcn/ui Toggle or Badge components for the chips

## Dependencies

### Requires
- 001-source-image-upload-page (image must be uploaded first)

### Enables
- 003-extraction-status-display (navigated to after submission)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| All 3 types selected | All 3 jobs queued |
| User deselects all after selecting | "Start Extraction" button disables |
| API returns error on submit | Toast error shown; user stays on selection page |

## Out of Scope

- Custom prompt input (garment type chips map to prompts internally)
- Sub-garment categories (e.g., "shirt" vs "jacket") — out of scope for MVP

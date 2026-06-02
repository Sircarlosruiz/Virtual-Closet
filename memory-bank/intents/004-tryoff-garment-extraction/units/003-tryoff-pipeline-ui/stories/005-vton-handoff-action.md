---
id: 005-vton-handoff-action
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
status: complete
priority: should
created: 2026-05-31T00:00:00.000Z
assigned_bolt: 020-tryoff-pipeline-ui
implemented: true
---

# Story: 005-vton-handoff-action

## User Story

**As a** mayorista
**I want** a "Use in VTON" button on each extracted garment
**So that** I can apply it to a different model in the VTON pipeline without re-uploading

## Acceptance Criteria

- [ ] **Given** an extraction job is `complete`, **When** I see the job card or media gallery item, **Then** a "Use in VTON" button is visible
- [ ] **Given** I click "Use in VTON", **When** the navigation happens, **Then** I am taken to the VTON job submission page (`/vton/new`) with the extracted garment pre-filled in the garment field
- [ ] **Given** I arrive at the VTON submission page, **When** the page loads, **Then** the garment thumbnail and type are shown as pre-selected — I only need to pick a model and click Submit
- [ ] **Given** the VTON submission page already has a garment selected, **When** I navigate via "Use in VTON", **Then** the new garment replaces the previous selection (no merge)

## Technical Notes

- Navigation: `router.push("/vton/new?garment_id=<media_id>")`
- VTON submission page must read `garment_id` from query params and pre-populate the garment field
- This story only covers the TryOff side — the VTON page's query param reading is part of the VTON pipeline UI (intent 001) — coordinate with that unit's stories
- No new API call needed; navigation passes the media ID; VTON page fetches garment details using existing media API
- Button label: "Use in VTON ↗" (indicates navigation away)

## Dependencies

### Requires
- 004-extracted-garment-gallery (button appears here too)
- 003-extraction-status-display (button appears on completed job cards)
- 001-vton-generation-pipeline / vton-pipeline-ui (must accept `?garment_id` query param)

### Enables
- Closed-loop flow: TryOff → VTON

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Extracted garment media item deleted before clicking | VTON page shows "Garment not found" and clears the field |
| User is on mobile | Button is accessible (not hidden behind hover state) |
| VTON page not yet updated to accept query param | Button navigates anyway; garment field starts empty (graceful degradation) |

## Out of Scope

- Automatically submitting the VTON job (user must still select a model and confirm)
- Sharing extracted garments with other mayoristas

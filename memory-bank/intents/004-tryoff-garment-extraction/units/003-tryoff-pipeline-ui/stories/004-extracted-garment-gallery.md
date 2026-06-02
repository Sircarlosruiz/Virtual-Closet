---
id: 004-extracted-garment-gallery
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
status: complete
priority: must
created: 2026-05-31T00:00:00.000Z
assigned_bolt: 020-tryoff-pipeline-ui
implemented: true
---

# Story: 004-extracted-garment-gallery

## User Story

**As a** mayorista
**I want** to see all my extracted garments in my media library
**So that** I can browse and reuse them for future VTON jobs

## Acceptance Criteria

- [ ] **Given** I open the media library, **When** I apply the filter "Extracted Garments", **Then** only items with `type: extracted_garment` are shown
- [ ] **Given** the filtered gallery, **When** I see each item, **Then** it displays the garment thumbnail, garment type label (Upper / Lower / Dress), and extraction date
- [ ] **Given** an extracted garment item, **When** I click on it, **Then** a detail panel opens showing the full-size image, source image reference, and "Use in VTON" button
- [ ] **Given** no extracted garments exist yet, **When** the filter is active, **Then** I see an empty state with a CTA "Extract your first garment"

## Technical Notes

- Filter integration: add "Extracted Garments" chip to existing media library filter bar
- Query: `/api/media?type=extracted_garment&page=1&page_size=24`
- Thumbnail grid: reuse existing media library grid component with garment type badge overlay
- Detail panel: reuse existing media item detail drawer/sheet
- "Use in VTON" navigates to `/vton/new?garment_id=<media_id>`

## Dependencies

### Requires
- 002-tryoff-job-service/005-media-library-save (items must exist in media library)

### Enables
- 005-vton-handoff-action (accessible from both this gallery and status page)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Garment thumbnail not yet available (race condition) | Show skeleton placeholder; auto-refreshes |
| Very large media library (100+ extracted garments) | Pagination works correctly |
| Garment from a failed job | Not shown (only `complete` jobs create MediaItems) |

## Out of Scope

- Organizing extracted garments into folders or collections (intent 002)
- Deleting extracted garments from the media library
- Bulk selection and export

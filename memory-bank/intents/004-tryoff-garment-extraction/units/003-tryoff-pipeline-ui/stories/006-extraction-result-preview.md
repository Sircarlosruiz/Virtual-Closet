---
id: 006-extraction-result-preview
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
status: complete
priority: should
created: 2026-06-03T00:00:00.000Z
assigned_bolt: 021-tryoff-pipeline-ui
implemented: true
---

# Story: 006-extraction-result-preview

## User Story

**As a** mayorista
**I want** to see the extracted garment at full size on its flat/white background after the job completes
**So that** I can inspect the result clearly and decide whether to use it in the VTON pipeline or download it

## Acceptance Criteria

- [ ] **Given** a TryOff job is `complete`, **When** I click the garment thumbnail on the extraction status page, **Then** a full-size preview modal/lightbox opens showing the extracted garment on its flat white background
- [ ] **Given** the full-size preview is open, **When** I look at the available actions, **Then** I see a "Use in VTON" button and a "Download" button prominently displayed
- [ ] **Given** the full-size preview is open, **When** I click "Use in VTON", **Then** the modal closes and I am navigated to `/vton/new?garment_id=<media_id>` with the garment pre-filled
- [ ] **Given** the full-size preview is open, **When** I click "Download", **Then** the garment PNG downloads to my device with a meaningful filename (e.g. `extracted-upper-<job_id>.png`)
- [ ] **Given** the full-size preview is open, **When** I click outside the modal or press Escape, **Then** the modal closes and I return to the status page
- [ ] **Given** I am in the media library detail panel for an extracted garment, **When** I view the detail panel, **Then** the same full-size flat background display and "Use in VTON" + download actions are available (reusing the same preview component)

## Technical Notes

- Reuse the existing shadcn/ui `Dialog` or `Sheet` component as the lightbox container
- Image displayed at maximum readable size within the viewport; no upscaling past native resolution
- "Use in VTON" navigates to `/vton/new?garment_id=<media_id>` (same route as story 005)
- "Download" uses a `<a download>` anchor pointing to the media item's storage URL (`/api/media/<id>/download` or direct MinIO presigned URL)
- Filename convention: `extracted-<garment_type>-<job_id>.png`
- The preview component must be usable from both the status page (story 003) and the media library detail panel (story 004) — extract as a shared component `<GarmentPreviewModal />`
- No new API endpoint needed; image URL already available from the completed job or media item object

## Dependencies

### Requires
- 003-extraction-status-display (thumbnail click trigger)
- 004-extracted-garment-gallery (reuse from media library detail panel)
- 002-tryoff-job-service/005-media-library-save (media item must exist to have a URL)

### Enables
- Closes the inspection loop: extraction → preview → VTON or download

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Image URL expires (MinIO presigned URL) | Fetch a fresh presigned URL on modal open; show error toast if fetch fails |
| Image is very large (> 4 MB PNG) | Browser renders natively; no client-side resize needed |
| User on mobile (small viewport) | Modal uses full-screen on mobile; image scales to fit within safe area |
| Job result deleted from storage | Show "Image no longer available" message with only "Close" action |

## Out of Scope

- Editing or cropping the extracted garment image
- Comparing the extracted garment with the source photo side-by-side
- Sharing the garment image with other mayoristas

---
stage: plan
bolt: 021-tryoff-pipeline-ui
created: 2026-06-03T00:00:00Z
---

## Implementation Plan: 021-tryoff-pipeline-ui

### Objective

Create a shared `<GarmentPreviewModal />` component that displays extracted garments at full size on their flat white background, with "Use in VTON" and "Download" actions. Integrate it into both the status page (triggered by clicking a completed job card thumbnail) and the media library detail panel (replacing the current inline Sheet image).

### Deliverables

1. **`components/tryoff/garment-preview-modal.tsx`** — Shared preview modal component
   - Accepts `garment` object (image URL, garment type, media ID, job ID)
   - Uses `Dialog` from `@base-ui/react/dialog` (create `components/ui/dialog.tsx` wrapper)
   - Full-size image display (no upscaling past native resolution)
   - "Use in VTON" button → navigates to `/dashboard/generate?garment_id=<media_id>`
   - "Download" button → triggers browser download with filename `extracted-<garment_type>-<job_id>.png`
   - Closes on Escape, click outside (backdrop), or close button
   - Mobile responsive: full-screen on small viewports
   - Handles expired presigned URLs (shows error toast on fetch failure)
   - Handles missing/deleted images (shows "Image no longer available" message)

2. **`components/ui/dialog.tsx`** — shadcn Dialog component wrapping `@base-ui/react/dialog`
   - Follows same pattern as existing `sheet.tsx`

3. **`components/tryoff/job-card.tsx`** — Updated to trigger preview modal on thumbnail click
   - Click on completed job thumbnail opens `GarmentPreviewModal`
   - Passes `output_url`, `garment_type`, `output_media_id`, `job_id`

4. **`components/tryoff/extracted-garments-grid.tsx`** — Updated to use `GarmentPreviewModal` in detail Sheet
   - Replace the current inline `<img>` in the Sheet with the shared preview component
   - Preserves existing "Use in VTON" behavior

### Dependencies

- **019-tryoff-pipeline-ui**: Status page (`JobList`, `JobCard`) and upload flow must exist
- **020-tryoff-pipeline-ui**: Media library (`ExtractedGarmentsGrid`, `ExtractedGarmentCard`) must exist
- **`@base-ui/react`**: Already installed (Sheet uses it)
- **No new API endpoints**: Image URLs already available from job/media item objects

### Technical Approach

1. **Dialog component**: Create `components/ui/dialog.tsx` wrapping `@base-ui/react/dialog` following the same pattern as `sheet.tsx` (which already uses `Dialog as SheetPrimitive`). Export: `Dialog`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogFooter`, `DialogTitle`, `DialogDescription`, `DialogClose`.

2. **GarmentPreviewModal**: Client component (`"use client"`).
   - Props: `{ imageUrl, garmentType, mediaId, jobId, filename?, open, onOpenChange }`
   - State: `imageError` (for expired/missing URLs), `isDownloading` (for download feedback)
   - Layout: Centered image in Dialog, action buttons below (flex row)
   - Image: `max-w-full max-h-[80vh] object-contain` — no upscaling, fits viewport
   - Download: Create `<a download>` element with `imageUrl`, set `download` attribute to filename
   - VTON handoff: `router.push(`/dashboard/generate?garment_id=${mediaId}`)` then `onOpenChange(false)`
   - Error handling: If image fails to load (`onError`), show fallback message with only "Close" button

3. **JobCard integration**:
   - Add `onClick` handler to the thumbnail `<img>` wrapper
   - On click, set local state to open the modal with job data
   - Render `<GarmentPreviewModal>` at the bottom of the component (conditional on open state)

4. **ExtractedGarmentsGrid integration**:
   - The existing Sheet already shows full-size image + "Use in VTON"
   - Replace the inline `<img>` with `<GarmentPreviewModal>` passing the selected garment's data
   - Keep the Sheet as the container, the modal content replaces the current image section

### Acceptance Criteria

- [ ] Clicking garment thumbnail on status page opens full-size preview modal
- [ ] Modal shows "Use in VTON" and "Download" buttons
- [ ] "Use in VTON" navigates to `/dashboard/generate?garment_id=<media_id>`
- [ ] "Download" saves PNG with filename `extracted-<garment_type>-<job_id>.png`
- [ ] Modal closes on Escape or click outside backdrop
- [ ] Same preview component reused in media library detail panel (Sheet)
- [ ] Expired presigned URL handled gracefully with error toast
- [ ] Missing/deleted image shows "Image no longer available" message
- [ ] Mobile: modal uses full-screen; image scales to fit viewport
- [ ] No new API endpoints added
- [ ] ESLint passes, TypeScript strict mode satisfied

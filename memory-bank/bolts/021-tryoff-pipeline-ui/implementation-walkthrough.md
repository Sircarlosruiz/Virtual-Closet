---
stage: implement
bolt: 021-tryoff-pipeline-ui
created: 2026-06-03T00:00:00Z
---

## Implementation Walkthrough: 021-tryoff-pipeline-ui

### Summary

Created a shared `GarmentPreviewModal` component that displays extracted garments at full size with "Use in VTON" and "Download" actions. Integrated it into the status page (thumbnail click opens modal) and media library (replaced Sheet detail with Dialog modal). Also created the missing `Dialog` UI component wrapping `@base-ui/react/dialog`.

### Structure Overview

- New Dialog UI component following the same pattern as existing Sheet
- GarmentPreviewModal as a reusable client component with image display, actions, and error handling
- JobCard updated with click-to-preview on completed job thumbnails
- ExtractedGarmentsGrid updated to use GarmentPreviewModal instead of Sheet detail panel

### Completed Work

- [x] `frontend/components/ui/dialog.tsx` — Dialog component (Root, Trigger, Close, Portal, Overlay, Content, Header, Footer, Title, Description)
- [x] `frontend/components/tryoff/garment-preview-modal.tsx` — Shared preview modal with full-size image, VTON handoff, download, error handling
- [x] `frontend/components/tryoff/job-card.tsx` — Updated: thumbnail click opens GarmentPreviewModal, keyboard accessible
- [x] `frontend/components/tryoff/extracted-garments-grid.tsx` — Updated: replaced Sheet detail with GarmentPreviewModal, removed unused imports

### Key Decisions

- **Dialog over Sheet for media library**: Using Dialog directly instead of nesting inside Sheet avoids modal-in-modal UX issues and provides a consistent preview experience across both status page and media library
- **Download via fetch + blob**: Uses `fetch()` to get the image blob then creates a download link, ensuring the filename is set correctly (presigned URLs don't carry meaningful filenames)
- **Error handling via toast**: Uses existing `sonner` toast library for user feedback on expired URLs and download failures
- **No Next.js Image component**: Using plain `<img>` for presigned URLs (consistent with existing codebase) since Next.js Image requires known domains in config

### Deviations from Plan

- None

### Dependencies Added

- None (all dependencies already present: `@base-ui/react`, `sonner`, `lucide-react`)

### Developer Notes

- The `GARMENT_LABELS` map is duplicated across `job-card.tsx`, `garment-preview-modal.tsx` — consider extracting to a shared constants file in a future refactor
- The Dialog component follows the same `@base-ui/react/dialog` pattern as Sheet — if base-ui updates its API, both files need updating together

---
id: 001-source-image-upload-page
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 019-tryoff-pipeline-ui
implemented: false
---

# Story: 001-source-image-upload-page

## User Story

**As a** mayorista
**I want** a page where I can upload a source photo of a model wearing clothing
**So that** I can start the garment extraction process

## Acceptance Criteria

- [ ] **Given** I navigate to `/tryoff/new`, **When** the page loads, **Then** I see a drag-and-drop upload area and a file picker button
- [ ] **Given** I select or drop an image file, **When** the file is chosen, **Then** a preview of the image appears immediately (before upload)
- [ ] **Given** the preview is shown, **When** I decide to change the image, **Then** I can clear and select a new file
- [ ] **Given** I select a non-image file (e.g., PDF), **When** I attempt to drop it, **Then** the upload is rejected with an error message "Please upload a JPEG or PNG image"
- [ ] **Given** I select a file > 10 MB, **When** I attempt to upload, **Then** an error message says "Image must be under 10 MB"

## Technical Notes

- Route: `/tryoff/new` (App Router page)
- Use shadcn/ui Dropzone or `react-dropzone` for file picker
- Preview: `URL.createObjectURL(file)` — no round-trip to server
- Image is uploaded to backend (POST /api/media/upload) only after garment type selection and "Start Extraction" click
- Accepted MIME types: `image/jpeg`, `image/png`
- Page uses existing app shell layout (sidebar + header)

## Dependencies

### Requires
- None (entry point of the TryOff flow)

### Enables
- 002-garment-type-selector (shown after image is selected)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Image is very large (> 4K resolution) | Accepted — backend handles it; no client-side resize for MVP |
| User navigates away mid-upload | Upload cancels; no orphan files created |
| Mobile browser (touch) | Tap to browse files (drag-and-drop optional on mobile) |

## Out of Scope

- Uploading from URL (only local file upload)
- Multiple source images per session
- Image cropping or editing

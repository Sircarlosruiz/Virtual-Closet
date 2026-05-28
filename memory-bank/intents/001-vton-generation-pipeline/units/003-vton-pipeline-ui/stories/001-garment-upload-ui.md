---
id: 001-garment-upload-ui
unit: 003-vton-pipeline-ui
intent: 001-vton-generation-pipeline
status: complete
priority: must
created: 2026-05-26T00:00:00.000Z
assigned_bolt: 004-vton-pipeline-ui
implemented: true
---

# Story: 001-garment-upload-ui

## User Story

**As a** mayorista
**I want** to upload a garment photo through the web interface
**So that** I can start the VTON generation flow

## Acceptance Criteria

- [ ] **Given** I am on the generate page, **When** I drag-and-drop or click to select a JPG/PNG file ≤ 10MB, **Then** a preview of the image is shown immediately (before upload)
- [ ] **Given** I have selected a valid file, **When** the file is uploaded to `POST /api/media/garments`, **Then** a loading indicator is shown during upload and a success state (thumbnail + checkmark) replaces it on completion
- [ ] **Given** I select a file with invalid type or size, **When** client-side validation runs, **Then** an inline error message is shown without making an API call
- [ ] **Given** the upload API returns an error, **When** the error is received, **Then** an inline error toast is shown with the server error message
- [ ] **Given** a garment photo is successfully uploaded, **When** I view the form, **Then** the uploaded photo is shown as "selected" and I can proceed to model selection

## Technical Notes

- Component: `GarmentUploader` (in `components/vton/`)
- Client-side validation before API call: type (JPG/PNG only), size (≤ 10MB)
- Use shadcn/ui `Input type="file"` + custom drag-and-drop zone
- Preview via `URL.createObjectURL()` — no upload needed for preview
- Upload progress indicator (indeterminate) during API call

## Dependencies

### Requires
- None (first UI step in the flow)

### Enables
- `003-vton-pipeline-ui/002-model-selection-ui`
- `003-vton-pipeline-ui/003-job-submission-ui`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User replaces already-uploaded garment photo | New upload replaces old; old presigned URL discarded |
| Upload interrupted (network loss) | Error toast shown; user can retry |
| Mobile: file picker instead of drag-and-drop | Native file picker works via `<input type="file">` |

## Out of Scope

- Multiple garment photo selection
- Photo cropping or editing

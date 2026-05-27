---
id: 001-upload-garment-photo
unit: 001-media-service
intent: 001-vton-generation-pipeline
status: complete
priority: must
created: 2026-05-26T00:00:00.000Z
assigned_bolt: 001-media-service
implemented: true
---

# Story: 001-upload-garment-photo

## User Story

**As a** mayorista
**I want** to upload a garment photo (flat or on mannequin)
**So that** I can use it as input for VTON generation

## Acceptance Criteria

- [ ] **Given** I am authenticated, **When** I POST a valid JPG/PNG ≤ 10MB to `POST /api/media/garments`, **Then** the file is stored in MinIO under my namespace and a `GarmentPhoto` record is created in PostgreSQL
- [ ] **Given** the upload succeeds, **When** I receive the response, **Then** it includes `{ id, presigned_url, filename, uploaded_at }` with a 15-minute presigned URL
- [ ] **Given** I upload a file with an unsupported type (e.g., GIF, PDF), **When** the request is processed, **Then** I receive HTTP 400 with `"Only JPG and PNG files are accepted"`
- [ ] **Given** I upload a file larger than 10MB, **When** the request is processed, **Then** I receive HTTP 400 with `"File size exceeds 10MB limit"`
- [ ] **Given** I am not authenticated, **When** I attempt an upload, **Then** I receive HTTP 401

## Technical Notes

- MinIO key format: `garments/{mayorista_id}/{uuid4}.{ext}`
- Use `multipart/form-data` request
- Validate content type from file header (magic bytes), not just the extension
- Store metadata in `garment_photos` PostgreSQL table

## Dependencies

### Requires
- None (foundational story)

### Enables
- `001-media-service/002-upload-own-model-photo` (same upload pattern)
- `002-vton-job-service/001-submit-vton-job` (needs garment photo ID)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| File with wrong extension but valid content | Accept based on magic bytes |
| Exactly 10MB file | Accepted |
| 10MB + 1 byte file | Rejected with size error |
| Concurrent uploads from same mayorista | Both succeed independently |

## Out of Scope

- Image resizing or thumbnail generation
- Background removal or preprocessing

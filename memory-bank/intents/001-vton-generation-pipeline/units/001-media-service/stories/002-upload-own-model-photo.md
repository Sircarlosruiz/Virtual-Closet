---
id: 002-upload-own-model-photo
unit: 001-media-service
intent: 001-vton-generation-pipeline
status: complete
priority: must
created: 2026-05-26T00:00:00.000Z
assigned_bolt: 001-media-service
implemented: true
---

# Story: 002-upload-own-model-photo

## User Story

**As a** mayorista
**I want** to upload my own model photos
**So that** I can use real models that match my brand when generating try-on images

## Acceptance Criteria

- [ ] **Given** I am authenticated, **When** I POST a valid JPG/PNG ≤ 10MB to `POST /api/media/models`, **Then** the file is stored in MinIO under my namespace and a `ModelPhoto` record is created with `is_curated=false`
- [ ] **Given** the upload succeeds, **When** I receive the response, **Then** it includes `{ id, presigned_url, label, is_curated, uploaded_at }`
- [ ] **Given** I have uploaded model photos, **When** I GET `GET /api/media/models/mine`, **Then** I receive a list of only my uploaded model photos (not curated ones)
- [ ] **Given** invalid file type or size, **When** I submit, **Then** same 400 validation errors as garment upload
- [ ] **Given** I am not authenticated, **When** I attempt an upload, **Then** I receive HTTP 401

## Technical Notes

- MinIO key format: `models/{mayorista_id}/{uuid4}.{ext}`
- `label` defaults to filename if not provided (optional field in request)
- `ModelPhoto` table has `is_curated` boolean column defaulting to `false` for own uploads

## Dependencies

### Requires
- `001-upload-garment-photo` (same upload infrastructure, reuse pattern)

### Enables
- `001-media-service/003-curated-model-library` (same model entity)
- `002-vton-job-service/001-submit-vton-job` (needs model photo ID)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Mayorista uploads photo of a mannequin (not a person) | Accepted — no content validation |
| Label not provided | Defaults to original filename |
| Delete own model photo | Not in scope for this story |

## Out of Scope

- Deleting model photos
- Editing model photo labels after upload
- Sharing model photos between mayoristas

---
id: 003-curated-model-library
unit: 001-media-service
intent: 001-vton-generation-pipeline
status: complete
priority: must
created: 2026-05-26T00:00:00.000Z
assigned_bolt: 001-media-service
implemented: true
---

# Story: 003-curated-model-library

## User Story

**As a** mayorista
**I want** to browse a curated library of model photos provided by the platform
**So that** I can generate try-on images without needing to upload my own model photos

## Acceptance Criteria

- [ ] **Given** I am authenticated, **When** I GET `GET /api/media/models/curated`, **Then** I receive a list of all curated model photos with `{ id, label, presigned_url, is_curated: true }`
- [ ] **Given** the curated library list is returned, **When** I inspect the response, **Then** `is_curated=true` for all items and no mayorista_id is present
- [ ] **Given** I try to upload a photo to the curated library via the mayorista API, **When** the request is processed, **Then** I receive HTTP 403 (curated library is read-only for mayoristas)
- [ ] **Given** I am not authenticated, **When** I attempt to list curated models, **Then** I receive HTTP 401

## Technical Notes

- Curated models stored in MinIO under a shared prefix: `models/curated/{uuid4}.{ext}`
- `ModelPhoto` records with `is_curated=true` and `mayorista_id=NULL` represent curated models
- Seeded by platform admins directly in DB/MinIO (no admin API in this intent)
- Pre-signed URLs generated at query time (15 min TTL)

## Dependencies

### Requires
- `002-upload-own-model-photo` (shares `ModelPhoto` entity)

### Enables
- `002-vton-job-service/001-submit-vton-job` (curated model IDs are valid inputs)
- `003-vton-pipeline-ui/002-model-selection-ui` (populates curated tab)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Curated library is empty (no seed data) | Returns empty list `[]`, not 404 |
| Mayorista uses curated model ID in job submission | Accepted — model_photo_id is valid |

## Out of Scope

- Admin API for adding/editing curated models
- Pagination of curated library (assumed small dataset for MVP)
- Filtering curated models by body type, ethnicity, etc.

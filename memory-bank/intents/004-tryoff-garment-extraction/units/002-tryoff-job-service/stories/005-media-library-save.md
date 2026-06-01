---
id: 005-media-library-save
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 017-tryoff-job-service
implemented: false
---

# Story: 005-media-library-save

## User Story

**As a** mayorista
**I want** my extracted garment images automatically saved to my media library
**So that** I can reuse them in future VTON jobs without re-uploading

## Acceptance Criteria

- [ ] **Given** a TryOff job completes, **When** the extracted garment PNG is received from the model container, **Then** it is saved to MinIO and a MediaItem is created in the mayorista's media library
- [ ] **Given** the MediaItem is created, **When** the mayorista views their media library, **Then** the extracted garment appears tagged with `type: extracted_garment` and `garment_type: upper|lower|dress`
- [ ] **Given** the MediaItem is created, **When** the mayorista opens the VTON submission form, **Then** the extracted garment is available in the garment picker
- [ ] **Given** the MinIO upload succeeds but the DB write fails, **When** the Celery task handles the error, **Then** it retries the full task (idempotent — overwrites MinIO object with same key)

## Technical Notes

- MediaItem stored with metadata JSON: `{ "type": "extracted_garment", "garment_type": "upper|lower|dress", "source_job_id": "<job_id>", "source_image_id": "<source_image_id>" }`
- MinIO path: `media/{mayorista_id}/extracted/{job_id}.png`
- Reuse existing MediaItem model — no schema changes, only metadata fields
- Tag filtering in media library query: `WHERE metadata->>'type' = 'extracted_garment'`

## Dependencies

### Requires
- 002-process-job-celery (output PNG must be available)

### Enables
- 003-tryoff-pipeline-ui/004-extracted-garment-gallery
- 003-tryoff-pipeline-ui/005-vton-handoff-action

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Duplicate save (idempotent retry) | MinIO overwrites existing object; DB upserts MediaItem by job_id |
| Output image < 768×1024 px | Saved as-is with a warning log; no blocking |
| Media library at storage quota | HTTP 507 from MinIO; job marked `failed` with quota error |

## Out of Scope

- Manual tagging or renaming by mayorista
- Organizing extracted garments into catalog collections (owned by intent 002)

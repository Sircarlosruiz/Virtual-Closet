---
id: 001-submit-vton-job
unit: 002-vton-job-service
intent: 001-vton-generation-pipeline
status: complete
priority: must
created: 2026-05-26T00:00:00.000Z
assigned_bolt: 002-vton-job-service
implemented: true
---

# Story: 001-submit-vton-job

## User Story

**As a** mayorista
**I want** to submit a VTON generation job by selecting a garment, a model, and a cloth type
**So that** the AI pipeline starts generating my try-on image

## Acceptance Criteria

- [ ] **Given** I am authenticated and provide valid `garment_photo_id`, `model_photo_id`, and `cloth_type`, **When** I POST to `POST /api/vton/generate`, **Then** I receive HTTP 201 with `{ job_id, status: "queued", created_at }` within 500ms
- [ ] **Given** the job is created, **When** I check PostgreSQL, **Then** a `VTONJob` record exists with `status=queued` and `retry_count=0`
- [ ] **Given** the job is created, **When** I check RabbitMQ, **Then** a task message was published for the Celery worker
- [ ] **Given** I provide an invalid `cloth_type` (not in `upper_body`, `lower_body`, `dress`), **When** I submit, **Then** I receive HTTP 400 with a validation error
- [ ] **Given** I reference a `garment_photo_id` that belongs to another mayorista, **When** I submit, **Then** I receive HTTP 403
- [ ] **Given** I reference a `model_photo_id` that does not exist, **When** I submit, **Then** I receive HTTP 404
- [ ] **Given** I am not authenticated, **When** I submit, **Then** I receive HTTP 401

## Technical Notes

- `cloth_type` validated against `ClothType` enum before job creation
- Cross-ownership check: `garment_photo_id` must belong to the authenticated mayorista
- `model_photo_id` can be own upload OR curated (both are valid `ModelPhoto` records)
- Celery task published after DB record committed (no message without persisted job)

## Dependencies

### Requires
- `001-media-service/001-upload-garment-photo` (garment_photo_id must exist)
- `001-media-service/002-upload-own-model-photo` or `003-curated-model-library` (model_photo_id must exist)

### Enables
- `002-vton-job-service/002-process-job-celery`
- `002-vton-job-service/003-poll-job-status`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Curated model photo used as model_photo_id | Accepted (is_curated=true is still a valid ModelPhoto) |
| Same garment + model submitted twice | Two independent jobs created |
| RabbitMQ unavailable at submission time | HTTP 503, job NOT created (atomicity: no orphaned jobs) |

## Out of Scope

- Batch job submission
- Specifying output image dimensions

---
id: 004-poll-job-status
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 017-tryoff-job-service
implemented: false
---

# Story: 004-poll-job-status

## User Story

**As a** mayorista
**I want** to check the status of my TryOff extraction job
**So that** I know when the garment image is ready to use

## Acceptance Criteria

- [ ] **Given** a valid job_id, **When** GET /api/tryoff/jobs/{job_id} is called, **Then** it returns the current status (`pending`, `processing`, `complete`, or `failed`) and estimated progress
- [ ] **Given** the job is `complete`, **When** the status is polled, **Then** the response includes `output_media_id` and a signed URL to the extracted garment image
- [ ] **Given** a job_id belonging to another mayorista, **When** polled, **Then** HTTP 404 is returned (not 403 — avoids enumeration)
- [ ] **Given** the job has failed, **When** polled, **Then** the response includes a human-readable `error_message`

## Technical Notes

- Endpoint: `GET /api/tryoff/jobs/{job_id}`
- Returns: `{ job_id, status, garment_type, output_media_id (nullable), output_url (signed URL, nullable), error_message (nullable), created_at, completed_at }`
- Signed URL TTL: 1 hour (same as existing media library)
- No server-sent events or WebSocket for MVP — polling only

## Dependencies

### Requires
- 001-submit-tryoff-job
- 002-process-job-celery (status transitions happen here)

### Enables
- 003-tryoff-pipeline-ui/003-extraction-status-display

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Job ID is malformed UUID | HTTP 422 |
| Job not yet picked up by worker | Returns `pending` with null output fields |

## Out of Scope

- WebSocket / SSE real-time updates
- Estimated time remaining

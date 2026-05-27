---
id: 005-job-history
unit: 002-vton-job-service
intent: 001-vton-generation-pipeline
status: complete
priority: should
created: 2026-05-26T00:00:00.000Z
assigned_bolt: 003-vton-job-service
implemented: true
---

# Story: 005-job-history

## User Story

**As a** mayorista
**I want** to see a list of my past VTON generation jobs
**So that** I can track what I've generated and access my results

## Acceptance Criteria

- [ ] **Given** I am authenticated, **When** I GET `GET /api/vton/jobs?page=1&page_size=20`, **Then** I receive a paginated list of my jobs ordered by `created_at DESC`
- [ ] **Given** the list is returned, **When** I inspect the response, **Then** each item includes `{ job_id, status, cloth_type, created_at, completed_at, result_url (if completed) }`
- [ ] **Given** a job in the list is `completed`, **When** `result_url` is included, **Then** it is a fresh 15-minute pre-signed URL
- [ ] **Given** I have no jobs, **When** I request history, **Then** I receive `{ items: [], total: 0 }`
- [ ] **Given** another mayorista's jobs exist, **When** I request history, **Then** they do not appear in my list
- [ ] **Given** I am not authenticated, **When** I request history, **Then** I receive HTTP 401

## Technical Notes

- Default ordering: `created_at DESC` (most recent first)
- `result_url` generated at query time for `completed` jobs
- Max `page_size`: 100
- Standard pagination format: `{ items: [...], total: N, page: N, page_size: N }`

## Dependencies

### Requires
- `002-vton-job-service/003-poll-job-status` (same VTONJob entity and access control pattern)

### Enables
- `003-vton-pipeline-ui/006-job-history-ui`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `page_size` > 100 | Clamped to 100 |
| `page` > total pages | Returns empty `items: []` |
| Mix of completed/failed/queued jobs | All returned, status visible per item |

## Out of Scope

- Filtering by status, cloth_type, or date range (future enhancement)
- Deleting jobs from history
- Downloading results in bulk

---
id: 007-job-history
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
status: draft
priority: should
created: 2026-05-31T00:00:00Z
assigned_bolt: 018-tryoff-job-service
implemented: false
---

# Story: 007-job-history

## User Story

**As a** mayorista
**I want** to see a list of my past TryOff extraction jobs
**So that** I can track what I've extracted and reuse results without re-running

## Acceptance Criteria

- [ ] **Given** a mayorista has submitted jobs, **When** GET /api/tryoff/jobs is called, **Then** it returns a paginated list of their TryoffJobs ordered by `created_at` descending
- [ ] **Given** the history list, **When** each job is displayed, **Then** it shows `job_id`, `garment_type`, `status`, `created_at`, and a thumbnail URL for completed jobs
- [ ] **Given** pagination parameters `page` and `page_size` (default 20), **When** the list is fetched, **Then** only the requested page is returned with a `total` count
- [ ] **Given** a mayorista has no past jobs, **When** the history is fetched, **Then** it returns an empty list (not 404)

## Technical Notes

- Endpoint: `GET /api/tryoff/jobs?page=1&page_size=20`
- Response: `{ jobs: TryoffJob[], total: int, page: int, page_size: int }`
- Thumbnail URL: signed MinIO URL (1h TTL) for `output_media_id` if status is `complete`
- Filter by `mayorista_id` from auth token (no cross-mayorista access)
- SQL: `SELECT * FROM tryoff_jobs WHERE mayorista_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?`

## Dependencies

### Requires
- 001-submit-tryoff-job (jobs must exist)
- 004-poll-job-status (shared data model)

### Enables
- 003-tryoff-pipeline-ui/003-extraction-status-display (history page)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `page_size` > 100 | Clamped to 100 |
| Negative `page` | HTTP 422 |
| Jobs from multiple sessions mixed | All returned in date order (no session grouping) |

## Out of Scope

- Filtering by garment type or status
- Deleting past jobs from history
- Exporting history as CSV

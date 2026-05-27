---
id: 004-job-status-polling-ui
unit: 003-vton-pipeline-ui
intent: 001-vton-generation-pipeline
status: draft
priority: must
created: 2026-05-26T00:00:00Z
assigned_bolt: 005-vton-pipeline-ui
implemented: false
---

# Story: 004-job-status-polling-ui

## User Story

**As a** mayorista
**I want** to see my job's progress update automatically
**So that** I know when my try-on image is ready without refreshing the page

## Acceptance Criteria

- [ ] **Given** I land on `/dashboard/jobs/{job_id}`, **When** the job is `queued` or `processing`, **Then** the page polls `GET /api/vton/jobs/{job_id}` every 5 seconds automatically
- [ ] **Given** polling is active, **When** the job transitions to `processing`, **Then** the UI updates to show a "Processing..." state with an animated indicator
- [ ] **Given** polling is active, **When** the job transitions to `completed`, **Then** polling stops and the result display is shown (see story 005)
- [ ] **Given** polling is active, **When** the job transitions to `failed`, **Then** polling stops and the failure state is shown with the error reason
- [ ] **Given** the page is closed or navigated away, **When** the component unmounts, **Then** polling stops (no background requests)
- [ ] **Given** a poll request fails (network error), **When** the error occurs, **Then** polling continues (retry on next interval) — minor transient errors do not stop polling

## Technical Notes

- Implement with SWR `refreshInterval: 5000` or React Query with `refetchInterval`
- Stop polling: set `refreshInterval: 0` (SWR) or `refetchInterval: false` (React Query) when status is `completed` or `failed`
- Status states to display:
  - `queued`: "In queue..." with a spinner
  - `processing`: "Generating your try-on..." with animated progress bar
  - `completed`: (handled in story 005)
  - `failed`: (handled in story 005)
- Estimated wait time displayed (optional): "Usually takes 30-120 seconds"

## Dependencies

### Requires
- `003-vton-pipeline-ui/003-job-submission-ui` (redirects here after submit)

### Enables
- `003-vton-pipeline-ui/005-result-display-ui` (shown when job completes)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User opens job status page directly (via URL) | Works — loads current status and starts polling if needed |
| Job already `completed` when page loads | No polling started; go directly to result display |
| API returns 403 (wrong mayorista) | Show "Job not found" error, do not poll |

## Out of Scope

- WebSocket real-time updates
- Push notifications when job completes
- Estimated time remaining countdown

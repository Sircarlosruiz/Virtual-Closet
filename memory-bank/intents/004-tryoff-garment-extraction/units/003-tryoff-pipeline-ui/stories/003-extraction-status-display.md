---
id: 003-extraction-status-display
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 019-tryoff-pipeline-ui
implemented: false
---

# Story: 003-extraction-status-display

## User Story

**As a** mayorista
**I want** to see live status updates for my extraction jobs
**So that** I know when each garment image is ready without refreshing the page

## Acceptance Criteria

- [ ] **Given** I submit garment extraction jobs, **When** I land on the status page, **Then** I see a card per job showing garment type and a `Pending` status badge
- [ ] **Given** the page is displayed, **When** a job transitions to `processing`, **Then** the card updates to show a spinner and `Processing` badge without a full page reload
- [ ] **Given** a job completes, **When** the status is polled, **Then** the card shows the extracted garment thumbnail and a `Complete` badge
- [ ] **Given** a job fails (after retries), **When** the status is polled, **Then** the card shows a `Failed` badge with the error message
- [ ] **Given** all jobs are complete or failed, **When** the polling loop checks, **Then** polling stops (no unnecessary API calls after terminal states)

## Technical Notes

- Route: `/tryoff/status?session_image_id=<id>` or `/tryoff/status?job_ids=<id1>,<id2>`
- Polling: SWR `refreshInterval` starting at 2s, backing off to 10s cap using `refreshInterval` function
- Stop polling when all jobs in terminal state (`complete` or `failed`)
- Each job card: garment type label, status badge, thumbnail (when complete), "Use in VTON" button (when complete)
- shadcn/ui Card + Badge + Skeleton for loading state

## Dependencies

### Requires
- 002-garment-type-selector (arrives here after submission)
- 002-tryoff-job-service/004-poll-job-status (backend API)

### Enables
- 004-extracted-garment-gallery (completed jobs appear in media library)
- 005-vton-handoff-action (button appears on completed job cards)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User navigates away and returns | Jobs still visible in history page (story 004) |
| One job fails, another completes | Mixed badge states on same page; polling stops when all are terminal |
| Session with only 1 garment type | Single card displayed |

## Out of Scope

- WebSocket / SSE real-time push
- Estimated time remaining countdown
- Cancelling in-progress jobs

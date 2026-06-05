---
id: 002-batch-progress-page
unit: 002-batch-vton-generation-ui
intent: 005-batch-vton-generation
status: complete
priority: must
created: 2026-06-04T00:00:00Z
assigned_bolt: 026-batch-vton-generation-ui
implemented: true
---

# Story: 002-batch-progress-page

## User Story

**As a** mayorista
**I want** to see real-time progress for my batch with per-item status
**So that** I know exactly how many jobs are done, in progress, or failed without refreshing manually

## Acceptance Criteria

- [ ] **Given** I am on the `BatchProgressPage`, **When** the page loads, **Then** I see the batch name, overall progress bar (e.g., "14 / 20"), and counts for completed/failed/in-progress
- [ ] **Given** the batch is active (`status: in-progress`), **When** the page is open, **Then** status updates automatically every 3 seconds via polling
- [ ] **Given** the batch reaches a terminal state (`complete`, `partial`, `failed`), **When** the status is received, **Then** polling stops and a summary banner is shown
- [ ] **Given** the per-item list, **When** rendered, **Then** each row shows: garment thumbnail, model thumbnail, cloth type, and a status badge (Pending / Processing / Done / Failed)
- [ ] **Given** an item has `status: failed`, **When** rendered, **Then** the error message is displayed under the item row (truncated to 120 chars with expand)
- [ ] **Given** the batch is complete, **When** a completed item is clicked, **Then** the result image opens in the media library

## Technical Notes

- Use `setInterval` (or React Query `refetchInterval`) to poll `GET /api/batches/{id}` every 3s
- Clear interval when `batch.status` ∈ `['complete', 'partial', 'failed']`
- Status badges: Pending (gray), Processing (blue spinner), Done (green check), Failed (red X)
- Progress bar: `completed_count / total_items` (does not count in-progress or failed)

## Dependencies

### Requires
- 001-batch-creation-flow (redirected here after submit)

### Enables
- 003-retry-failed-item-ui (retry button appears on this page)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Navigating away while batch is active | Polling stops; progress continues server-side |
| Network error during poll | Show "Connection lost" indicator; resume polling when reconnected |
| 100-item batch with all items showing | Virtualized list to avoid performance issues |

## Out of Scope

- WebSocket real-time updates (polling is sufficient for V1)
- Cancelling an in-progress batch

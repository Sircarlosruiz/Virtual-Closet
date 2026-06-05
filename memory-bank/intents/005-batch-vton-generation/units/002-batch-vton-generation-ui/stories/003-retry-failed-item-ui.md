---
id: 003-retry-failed-item-ui
unit: 002-batch-vton-generation-ui
intent: 005-batch-vton-generation
status: draft
priority: must
created: 2026-06-04T00:00:00Z
assigned_bolt: 027-batch-vton-generation-ui
implemented: false
---

# Story: 003-retry-failed-item-ui

## User Story

**As a** mayorista
**I want** to retry a failed batch item with one click from the progress page
**So that** I can recover individual failures without resubmitting the whole batch

## Acceptance Criteria

- [ ] **Given** a batch item has `status: failed`, **When** rendered in the progress page, **Then** a "Retry" button appears on that row
- [ ] **Given** I click "Retry", **When** the button is clicked, **Then** the button shows a loading spinner, the row status badge optimistically updates to "Pending", and `POST /api/batches/{id}/items/{item_id}/retry` is called
- [ ] **Given** the retry API responds successfully, **When** the response arrives, **Then** the spinner is removed and the row status remains "Pending"
- [ ] **Given** the retry API returns an error, **When** the response arrives, **Then** an inline error message is shown on the row and the status badge reverts to "Failed"
- [ ] **Given** an item has `status: processing` or `status: complete`, **When** rendered, **Then** no "Retry" button is shown

## Technical Notes

- Optimistic update: set local row status to `pending` before API response returns
- Disable the Retry button while the POST is in flight to prevent double-clicks
- After retry, the existing 3s polling will pick up the new status; no manual refresh needed

## Dependencies

### Requires
- 002-batch-progress-page (retry button lives on the progress page item rows)

### Enables
- None (terminal UI interaction)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User retries same item twice quickly | Button disabled while request in flight; second click ignored |
| API returns 409 (item already pending) | Show "Item already queued" message; revert optimistic update |

## Out of Scope

- Bulk retry all failed items at once (future enhancement)

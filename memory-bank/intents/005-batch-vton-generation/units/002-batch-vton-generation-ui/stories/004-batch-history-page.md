---
id: 004-batch-history-page
unit: 002-batch-vton-generation-ui
intent: 005-batch-vton-generation
status: draft
priority: should
created: 2026-06-04T00:00:00Z
assigned_bolt: 027-batch-vton-generation-ui
implemented: false
---

# Story: 004-batch-history-page

## User Story

**As a** mayorista
**I want** to see a list of all my past and active batch jobs
**So that** I can monitor active batches and revisit completed ones

## Acceptance Criteria

- [ ] **Given** I navigate to the batch history page (`/batches`), **When** the page loads, **Then** I see a reverse-chronological list of my batches
- [ ] **Given** the batch list, **When** rendered, **Then** each row shows: batch name, created date, total items, completed count, failed count, and overall status badge
- [ ] **Given** I have no batches, **When** the page loads, **Then** an empty state is shown with a "Create your first batch" CTA linking to the new batch flow
- [ ] **Given** a batch has `status: in-progress`, **When** shown in the list, **Then** its counts update on each page visit (not live polling — static load)
- [ ] **Given** I click a batch row, **When** clicked, **Then** I am navigated to the `BatchProgressPage` for that batch
- [ ] **Given** there are more than 20 batches, **When** the page loads, **Then** pagination controls are shown

## Technical Notes

- No live polling on the history page — data is loaded once on mount
- Status badge colors: complete (green), partial (yellow), failed (red), in-progress (blue)
- Optionally add a "New Batch" shortcut button in the page header

## Dependencies

### Requires
- 001-batch-creation-flow (batches must exist to show)

### Enables
- None (informational page)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Batch name is very long | Truncated with ellipsis in the row |
| All batches failed | Table renders normally; status badges all show red |

## Out of Scope

- Filtering by date range or status
- Deleting a batch from the history list

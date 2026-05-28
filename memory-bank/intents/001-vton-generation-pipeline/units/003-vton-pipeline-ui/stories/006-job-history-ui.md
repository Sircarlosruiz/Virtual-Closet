---
id: 006-job-history-ui
unit: 003-vton-pipeline-ui
intent: 001-vton-generation-pipeline
status: complete
priority: should
created: 2026-05-26T00:00:00.000Z
assigned_bolt: 005-vton-pipeline-ui
implemented: true
---

# Story: 006-job-history-ui

## User Story

**As a** mayorista
**I want** to see a list of all my past VTON generation jobs
**So that** I can review what I've generated and access older results

## Acceptance Criteria

- [ ] **Given** I navigate to `/dashboard/jobs`, **When** the page loads, **Then** my past jobs are fetched from `GET /api/vton/jobs` and displayed in a list ordered newest first
- [ ] **Given** the list is shown, **When** I inspect each row, **Then** I see a thumbnail (for completed), cloth type label, status badge, and creation date
- [ ] **Given** I have no jobs, **When** the page loads, **Then** I see an empty state with "No generations yet" and a "Generate your first try-on" button
- [ ] **Given** I click a job row, **When** navigating, **Then** I am taken to `/dashboard/jobs/{job_id}` to see its details
- [ ] **Given** there are more jobs than `page_size=20`, **When** I scroll to the bottom, **Then** a "Load more" button or infinite scroll loads the next page

## Technical Notes

- Fetch: `GET /api/vton/jobs?page=1&page_size=20`
- Status badge colors: queued (gray), processing (blue), completed (green), failed (red) — shadcn/ui `Badge`
- Result thumbnail: `<Image>` with `result_url` for completed jobs; placeholder for others
- Pagination: "Load more" button appending next page (not full page replacement)
- Cloth type display: "Upper Body", "Lower Body", "Dress" (human-readable labels)

## Dependencies

### Requires
- `003-vton-pipeline-ui/005-result-display-ui` (thumbnails reuse same result image pattern)

### Enables
- Nothing (terminal story for this intent)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Mix of in-progress and completed jobs | In-progress rows show no thumbnail, just status badge |
| Failed job in list | Shows failed badge, no thumbnail, row still clickable |
| Network error on load | Error state with "Retry" button |

## Out of Scope

- Filtering by status or date
- Deleting jobs from history
- Bulk selection or export

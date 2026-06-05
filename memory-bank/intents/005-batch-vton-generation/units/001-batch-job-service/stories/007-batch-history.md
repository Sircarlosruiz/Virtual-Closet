---
id: 007-batch-history
unit: 001-batch-job-service
intent: 005-batch-vton-generation
status: complete
priority: should
created: 2026-06-04T00:00:00Z
assigned_bolt: 025-batch-job-service
implemented: true
---

# Story: 007-batch-history

## User Story

**As a** mayorista
**I want** to see a list of all my past and active batches
**So that** I can revisit results and monitor any batches still running

## Acceptance Criteria

- [ ] **Given** I call `GET /api/batches`, **When** authenticated as a mayorista, **Then** I receive a paginated list of my batches in reverse-chronological order
- [ ] **Given** the list response, **When** each batch row is inspected, **Then** it includes `{ batch_id, name, status, total_items, completed_count, failed_count, created_at }`
- [ ] **Given** I have 0 batches, **When** the endpoint is called, **Then** an empty list with `count: 0` is returned (not a 404)
- [ ] **Given** batches belonging to another mayorista exist, **When** I call `GET /api/batches`, **Then** they do not appear in my list
- [ ] **Given** pagination parameters `?page=2&page_size=10`, **When** applied, **Then** the correct subset of batches is returned with `next` and `previous` links

## Technical Notes

- DRF `ListAPIView` with `IsAuthenticated` and mayorista-scoped queryset filter
- Default page size: 20; max page size: 100
- Order by `-created_at`

## Dependencies

### Requires
- 001-create-batch-job (BatchJob records must exist)
- 003-track-item-status (counters must be accurate)

### Enables
- 004-batch-history-page (frontend story)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Batch still in-progress | Appears in list with current `in-progress` status and live counters |
| Very large history (1000+ batches) | Pagination prevents performance issues |

## Out of Scope

- Deleting or archiving batches
- Filtering by date range (future enhancement)

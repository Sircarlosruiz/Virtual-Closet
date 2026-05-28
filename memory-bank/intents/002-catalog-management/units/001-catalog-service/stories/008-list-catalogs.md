---
id: 008-list-catalogs
unit: 001-catalog-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 007-catalog-service
implemented: true
---

# Story: 008-list-catalogs

## User Story

**As a** mayorista
**I want** to see a paginated list of all my catalogs
**So that** I can manage my collections at a glance

## Acceptance Criteria

- [ ] **Given** I am authenticated, **When** I GET `/api/catalogs`, **Then** I receive `{ catalogs: [...], total, page, page_size }` with only my own catalogs
- [ ] **Given** each catalog entry, **When** returned, **Then** it includes `catalog_id, name, status, item_count, created_at, updated_at`
- [ ] **Given** pagination params `?page=2&page_size=10`, **When** applied, **Then** correct page of results is returned
- [ ] **Given** I have no catalogs, **When** I list, **Then** I receive `{ catalogs: [], total: 0, page: 1 }`
- [ ] **Given** I am NOT authenticated, **When** I GET `/api/catalogs`, **Then** I receive 401

## Technical Notes

- Default pagination: `page=1, page_size=20`
- Ordered by `created_at DESC` by default
- `item_count` can be a DB annotation or a denormalized counter column

## Dependencies

### Requires
- 001-create-catalog

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `page` beyond total pages | Return empty `catalogs: []` with correct `total` |
| `page_size` > 100 | Clamp to 100 |
| `page_size` < 1 | 400 validation error |

## Out of Scope

- Filtering by status (draft/published)
- Search by name

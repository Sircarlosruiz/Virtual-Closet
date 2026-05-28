---
id: 001-catalog-list-page
unit: 003-catalog-management-ui
intent: 002-catalog-management
status: draft
priority: must
created: 2026-05-28T00:00:00Z
assigned_bolt: 009-catalog-management-ui
implemented: false
---

# Story: 001-catalog-list-page

## User Story

**As a** mayorista
**I want** to see all my catalogs in a dashboard
**So that** I can quickly understand the state of each collection and take action

## Acceptance Criteria

- [ ] **Given** I navigate to the catalogs section, **When** the page loads, **Then** I see all my catalogs as cards/rows showing: name, status badge (Draft/Published), item count, and last updated date
- [ ] **Given** I have no catalogs, **When** the page loads, **Then** I see an empty state with a "Create your first catalog" call-to-action
- [ ] **Given** I click "Create Catalog", **When** a form/modal appears, **Then** I can enter a name and submit to create a new draft catalog
- [ ] **Given** a new catalog is created, **When** the action completes, **Then** the new catalog appears in the list without a full page reload
- [ ] **Given** I click on a catalog, **When** navigated, **Then** I go to the catalog detail page

## Technical Notes

- Uses `GET /api/catalogs` — paginated, fetched via React Query
- Create catalog inline via modal → `POST /api/catalogs` → optimistic update or refetch
- Status badge: green for Published, grey for Draft

## Dependencies

### Requires
- 001-catalog-service APIs (list + create catalog)

### Enables
- 002-catalog-detail-page (navigate to detail from list)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| API error on load | Show error state with retry button |
| Long catalog name (> 50 chars) | Truncate with ellipsis in card |

## Out of Scope

- Filtering or searching catalogs
- Bulk actions on catalogs

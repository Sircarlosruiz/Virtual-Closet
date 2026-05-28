---
id: 002-catalog-detail-page
unit: 003-catalog-management-ui
intent: 002-catalog-management
status: draft
priority: must
created: 2026-05-28T00:00:00Z
assigned_bolt: 009-catalog-management-ui
implemented: false
---

# Story: 002-catalog-detail-page

## User Story

**As a** mayorista
**I want** to view and manage items within a specific catalog
**So that** I can add, remove, and reorder garments to build my collection

## Acceptance Criteria

- [ ] **Given** I open a catalog, **When** the page loads, **Then** I see the catalog name, status, and a grid/list of items showing: VTON image, garment name, price, cloth type, and SKU
- [ ] **Given** I click "Add Item", **When** a picker opens, **Then** I see my completed VTON results and can select one to add with a metadata form (name, price, cloth type, SKU)
- [ ] **Given** I click "Remove" on an item, **When** confirmed, **Then** the item disappears from the grid and item count updates
- [ ] **Given** I drag an item to a new position (or use reorder arrows), **When** I drop/confirm, **Then** the new order is saved via PATCH `.../reorder` and reflected immediately
- [ ] **Given** I click the catalog name, **When** I edit it inline or via modal, **Then** the name updates via PATCH

## Technical Notes

- Item images loaded as `<img src={preSignedUrl}>` — fetched fresh on page load (no cache)
- Add Item picker: calls `GET /api/vton/jobs?status=completed` from intent 001 API
- Reorder: optimistic UI update, then PATCH request with full ordered ID array
- Remove: confirmation modal before DELETE request

## Dependencies

### Requires
- 001-catalog-list-page (navigate from list)
- 001-catalog-service APIs (add, remove, reorder, rename)

### Enables
- 003-catalog-publish-flow

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| No completed VTON jobs available to add | "No results available yet" in picker |
| Reorder PATCH fails | Revert to previous order, show error toast |

## Out of Scope

- Editing item metadata after creation
- Bulk-adding multiple items at once

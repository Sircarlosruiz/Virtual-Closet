---
id: 003-remove-catalog-item
unit: 001-catalog-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 006-catalog-service
implemented: true
---

# Story: 003-remove-catalog-item

## User Story

**As a** mayorista
**I want** to remove a garment from a catalog
**So that** I can refine my collection before sharing it with buyers

## Acceptance Criteria

- [ ] **Given** I own the catalog and the item exists, **When** I DELETE `/api/catalogs/{catalog_id}/items/{item_id}`, **Then** the item is deleted and I receive 204
- [ ] **Given** the item is deleted, **When** I fetch the catalog, **Then** `item_count` decrements by 1 and the item no longer appears
- [ ] **Given** the catalog has 1 item with `status: published` and I delete it, **When** delete completes, **Then** the item is removed (catalog auto-unpublish is out of scope — validation happens at publish time only)
- [ ] **Given** the `item_id` does not exist in the catalog, **When** I delete, **Then** I receive 404
- [ ] **Given** the catalog belongs to a different mayorista, **When** I delete, **Then** I receive 403

## Technical Notes

- Remaining item positions are not re-normalized on delete — gaps in position sequence are acceptable
- `item_count` is a denormalized counter updated on add/remove operations (or computed via COUNT)

## Dependencies

### Requires
- 002-add-catalog-item (need items to remove)

### Enables
- None directly

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Deleting the only item from a published catalog | Delete succeeds; catalog may now be empty but stays published (state not auto-changed) |
| `catalog_id` valid but `item_id` from a different catalog | 404 |

## Out of Scope

- Bulk deletion of multiple items
- Soft-delete / undo functionality

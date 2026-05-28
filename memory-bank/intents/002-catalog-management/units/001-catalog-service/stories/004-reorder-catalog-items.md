---
id: 004-reorder-catalog-items
unit: 001-catalog-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 006-catalog-service
implemented: true
---

# Story: 004-reorder-catalog-items

## User Story

**As a** mayorista
**I want** to change the display order of items in my catalog
**So that** buyers see my garments in the sequence I intend

## Acceptance Criteria

- [ ] **Given** a catalog I own with items, **When** I PATCH `/api/catalogs/{catalog_id}/items/reorder` with `{ ordered_item_ids: [id3, id1, id2] }`, **Then** items are assigned positions `[1, 2, 3]` respectively and I receive 200 with the updated ordered list
- [ ] **Given** the `ordered_item_ids` array is missing any item that belongs to the catalog, **When** I submit, **Then** I receive 400 with "All catalog items must be included in the reorder request"
- [ ] **Given** the `ordered_item_ids` includes an ID not in this catalog, **When** I submit, **Then** I receive 400
- [ ] **Given** the catalog belongs to a different mayorista, **When** I reorder, **Then** I receive 403
- [ ] **Given** reorder succeeds, **When** I GET the catalog, **Then** items are returned in the new position order

## Technical Notes

- Reorder is an atomic DB transaction — all position updates or none
- Positions are re-normalized to consecutive integers (1, 2, 3...) after reorder
- `ordered_item_ids` must contain exactly the same set as current catalog items (bijection)

## Dependencies

### Requires
- 002-add-catalog-item (need ≥ 2 items to demonstrate reorder)

### Enables
- None directly

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Single-item catalog reorder | Succeeds trivially (no-op on position) |
| Empty `ordered_item_ids` array for non-empty catalog | 400 |
| Duplicate IDs in `ordered_item_ids` | 400 |

## Out of Scope

- Partial reorder (moving one item relative to others without specifying full order)

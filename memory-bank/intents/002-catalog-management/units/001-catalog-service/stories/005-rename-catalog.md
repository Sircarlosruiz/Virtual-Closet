---
id: 005-rename-catalog
unit: 001-catalog-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 007-catalog-service
implemented: true
---

# Story: 005-rename-catalog

## User Story

**As a** mayorista
**I want** to rename a catalog
**So that** I can update its title to reflect the correct collection name

## Acceptance Criteria

- [ ] **Given** I own the catalog, **When** I PATCH `/api/catalogs/{catalog_id}` with `{ name: "Winter 2026" }`, **Then** the name is updated and I receive the updated catalog object
- [ ] **Given** I submit an empty or whitespace-only name, **When** processed, **Then** I receive 400
- [ ] **Given** the catalog belongs to a different mayorista, **When** I rename, **Then** I receive 403
- [ ] **Given** I rename a published catalog, **When** a buyer fetches it, **Then** the new name is visible immediately

## Technical Notes

- PATCH endpoint handles both rename and publish/unpublish — use field presence to determine action
- Name update does not change `status` or any other field

## Dependencies

### Requires
- 001-create-catalog

### Enables
- None directly

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Name unchanged (same value) | 200 with no-op |
| Name is 101 characters | 400 validation error |

## Out of Scope

- Versioning or history of catalog names

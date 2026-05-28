---
id: 007-delete-catalog
unit: 001-catalog-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 007-catalog-service
implemented: true
---

# Story: 007-delete-catalog

## User Story

**As a** mayorista
**I want** to permanently delete a catalog
**So that** I can remove collections I no longer need

## Acceptance Criteria

- [ ] **Given** I own the catalog, **When** I DELETE `/api/catalogs/{catalog_id}`, **Then** the catalog and all its items are deleted and I receive 204
- [ ] **Given** the catalog is deleted, **When** I GET `/api/catalogs/{catalog_id}`, **Then** I receive 404
- [ ] **Given** the catalog was published, **When** it is deleted, **Then** buyers immediately receive 404 when accessing it in the portal
- [ ] **Given** the catalog belongs to a different mayorista, **When** I delete, **Then** I receive 403
- [ ] **Given** the catalog does not exist, **When** I delete, **Then** I receive 404

## Technical Notes

- Cascade delete: all `CatalogItem` records for the catalog are deleted in the same transaction
- Deletion is irreversible — no soft-delete or recovery
- VTON job records are NOT deleted (they belong to the VTON pipeline domain)

## Dependencies

### Requires
- 001-create-catalog

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Deleting a catalog with 0 items | Succeeds normally |
| Deleting a published catalog | Succeeds — buyers lose access immediately |

## Out of Scope

- Soft-delete or archive functionality
- Confirmation step (handled in UI layer)

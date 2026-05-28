---
unit: 001-catalog-service
intent: 002-catalog-management
phase: inception
status: complete
created: 2026-05-28T00:00:00.000Z
updated: 2026-05-28T00:00:00.000Z
default_bolt_type: ddd-construction-bolt
---

# Unit Brief: 001-catalog-service

## Purpose

Manages the full lifecycle of product catalogs and their items. A mayorista creates named collections, populates them with VTON-generated images plus product metadata, controls item ordering, and publishes or removes catalogs.

## Scope

### In Scope
- Creating and naming catalogs (draft status by default)
- Adding catalog items from completed VTON job results (image + garment metadata)
- Removing items from catalogs
- Reordering items within a catalog
- Renaming catalogs
- Publishing and unpublishing catalogs (draft ↔ published state machine)
- Deleting catalogs (cascade delete items)
- Listing a mayorista's catalogs (paginated, mayorista-scoped)

### Out of Scope
- Buyer portal authentication or catalog browsing (handled by 002-customer-portal-service)
- Frontend rendering (handled by 003-catalog-management-ui)
- VTON job execution (handled by 001-vton-generation-pipeline)
- PDF export of catalogs

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Catalog creation — `POST /api/catalogs` with `{name}`, returns draft catalog | Must |
| FR-2 | Add item — `POST /api/catalogs/{id}/items` with VTON job + metadata | Must |
| FR-3 | Remove item — `DELETE /api/catalogs/{id}/items/{item_id}` | Must |
| FR-4 | Reorder items — `PATCH /api/catalogs/{id}/items/reorder` | Must |
| FR-5 | Rename catalog — `PATCH /api/catalogs/{id}` with `{name}` | Must |
| FR-6 | Publish/unpublish — `PATCH /api/catalogs/{id}` with `{status}` | Must |
| FR-7 | Delete catalog — `DELETE /api/catalogs/{id}` (cascade) | Must |
| FR-8 | List catalogs — `GET /api/catalogs` paginated, mayorista-scoped | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| `Catalog` | Named collection owned by a mayorista | `id, mayorista_id, name, status (draft/published), item_count, created_at, updated_at` |
| `CatalogItem` | A single garment entry in a catalog | `id, catalog_id, vton_job_id, garment_name, price, cloth_type, sku, image_key (MinIO), position, created_at` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| CreateCatalog | Create draft catalog | `mayorista_id, name` | `Catalog` |
| AddItem | Validate job ownership + completion, create item | `catalog_id, vton_job_id, garment_name, price, cloth_type, sku` | `CatalogItem` |
| RemoveItem | Delete item, preserve remaining order | `catalog_id, item_id` | 204 |
| ReorderItems | Update `position` for all items atomically | `catalog_id, ordered_item_ids[]` | Updated items |
| PublishCatalog | Validate non-empty, set status=published | `catalog_id` | Updated `Catalog` |
| UnpublishCatalog | Set status=draft | `catalog_id` | Updated `Catalog` |
| DeleteCatalog | Cascade delete items, then catalog | `catalog_id` | 204 |
| ListCatalogs | Paginated, filtered by mayorista_id | `mayorista_id, page, page_size` | `Catalog[]` + total |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 8 |
| Must Have | 8 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-create-catalog | Create Named Catalog | Must | Planned |
| 002-add-catalog-item | Add Item to Catalog | Must | Planned |
| 003-remove-catalog-item | Remove Item from Catalog | Must | Planned |
| 004-reorder-catalog-items | Reorder Catalog Items | Must | Planned |
| 005-rename-catalog | Rename Catalog | Must | Planned |
| 006-publish-unpublish-catalog | Publish / Unpublish Catalog | Must | Planned |
| 007-delete-catalog | Delete Catalog | Must | Planned |
| 008-list-catalogs | List Mayorista's Catalogs | Must | Planned |

---

## Dependencies

### Depends On

| Unit / System | Reason |
|---------------|--------|
| VTON Pipeline (001-vton-generation-pipeline) | Reads completed job `result_url`, `cloth_type`, and `mayorista_id` from shared DB to validate item additions |

### Depended By

| Unit | Reason |
|------|--------|
| `002-customer-portal-service` | Reads published catalogs and their items for the buyer portal |
| `003-catalog-management-ui` | Consumes all catalog and item APIs |

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| PostgreSQL | Persists Catalog and CatalogItem records | Low (same DB as VTON pipeline) |
| MinIO | Generates pre-signed URLs for item image keys | Low (same MinIO as VTON pipeline) |

---

## Technical Context

### Suggested Technology
- Django REST Framework (consistent with VTON pipeline)
- PostgreSQL via Django ORM
- MinIO SDK for pre-signed URL generation (same pattern as intent 001)

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| VTON job read | Internal DB | Django ORM cross-app query |
| MinIO pre-signed URL | Outbound | MinIO SDK (same client as intent 001) |

### Data Storage

| Data | Type | Notes |
|------|------|-------|
| Catalog records | PostgreSQL | `catalog` table, mayorista-scoped |
| CatalogItem records | PostgreSQL | `catalog_item` table, FK to catalog + vton_job |

---

## Constraints

- Item `vton_job_id` must reference a job with `status: completed` owned by the same mayorista
- A catalog with 0 items cannot be published (return 422)
- `position` values are maintained as integers; reorder is atomic (transaction)
- Image URLs are generated on-demand via MinIO pre-signed URLs — `image_key` (not URL) is stored in DB

---

## Success Criteria

### Functional
- [ ] All 8 story acceptance criteria pass
- [ ] Mayorista can only access their own catalogs (row-level isolation)
- [ ] Adding an item from another mayorista's job returns 403

### Non-Functional
- [ ] Catalog list p95 < 300ms
- [ ] Item add/reorder p95 < 300ms

### Quality
- [ ] Code coverage > 80%
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 006-catalog-service | ddd-construction-bolt | 001, 002, 003, 004 | Core domain model + item CRUD |
| 007-catalog-service | ddd-construction-bolt | 005, 006, 007, 008 | Catalog lifecycle + list |

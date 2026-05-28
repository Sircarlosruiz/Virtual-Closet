---
id: 002-add-catalog-item
unit: 001-catalog-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 006-catalog-service
implemented: true
---

# Story: 002-add-catalog-item

## User Story

**As a** mayorista
**I want** to add a completed VTON result to a catalog with product metadata
**So that** my buyers can see the garment image alongside its name, price, and details

## Acceptance Criteria

- [ ] **Given** a completed VTON job I own, **When** I POST `/api/catalogs/{catalog_id}/items` with `{ vton_job_id, garment_name, price, cloth_type, sku }`, **Then** the item is created and I receive `{ item_id, image_url (pre-signed), garment_name, price, cloth_type, sku, position }`
- [ ] **Given** the `vton_job_id` references a job with `status != completed`, **When** I submit, **Then** I receive 422 with "Job must be completed before adding to catalog"
- [ ] **Given** the `vton_job_id` belongs to a different mayorista, **When** I submit, **Then** I receive 403
- [ ] **Given** the `catalog_id` belongs to a different mayorista, **When** I submit, **Then** I receive 403
- [ ] **Given** item is created, **When** I fetch the catalog, **Then** `item_count` increments by 1 and the item appears last in position order

## Technical Notes

- `image_url` in the response is a MinIO pre-signed URL generated on demand (not stored)
- The stored field is `image_key` (MinIO object key from the VTON job result)
- `position` is assigned as `MAX(position) + 1` for the catalog (appended last)
- `price` stored as DECIMAL(10,2); accept string or number in request

## Dependencies

### Requires
- 001-create-catalog (need an existing catalog)

### Enables
- 003-remove-catalog-item
- 004-reorder-catalog-items
- 006-publish-unpublish-catalog (needs at least 1 item to publish)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `vton_job_id` does not exist | 404 |
| `garment_name` is empty | 400 validation error |
| `price` is negative | 400 validation error |
| Adding same VTON job to same catalog twice | Allowed (duplicate items permitted) |
| `cloth_type` value not in `{upper_body, lower_body, dress}` | 400 validation error |

## Out of Scope

- Batch-adding multiple items in one request
- Editing item metadata after creation (separate story if needed)

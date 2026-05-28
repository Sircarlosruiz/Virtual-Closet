---
id: 006-publish-unpublish-catalog
unit: 001-catalog-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 007-catalog-service
implemented: true
---

# Story: 006-publish-unpublish-catalog

## User Story

**As a** mayorista
**I want** to publish or unpublish a catalog
**So that** I control when buyers can access it in the portal

## Acceptance Criteria

- [ ] **Given** I own a draft catalog with at least 1 item, **When** I PATCH `/api/catalogs/{catalog_id}` with `{ status: "published" }`, **Then** status changes to `published` and buyers can see it in the portal immediately
- [ ] **Given** I own a published catalog, **When** I PATCH with `{ status: "draft" }`, **Then** status changes to `draft` and the catalog is immediately hidden from the buyer portal (returns 404 to buyers)
- [ ] **Given** the catalog has 0 items, **When** I attempt to publish, **Then** I receive 422 with "Cannot publish an empty catalog"
- [ ] **Given** the catalog belongs to a different mayorista, **When** I change status, **Then** I receive 403
- [ ] **Given** `status` value is not `published` or `draft`, **When** I submit, **Then** I receive 400

## Technical Notes

- Status transitions: `draft → published` and `published → draft` are both valid
- No intermediate states (e.g., `scheduled`, `archived`) in scope
- Publishing is instant — no background job needed

## Dependencies

### Requires
- 001-create-catalog
- 002-add-catalog-item (publishing requires at least 1 item)

### Enables
- 003-browse-published-catalogs in 002-customer-portal-service (needs published catalogs to browse)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Publishing already-published catalog | Idempotent — 200 with no state change |
| Unpublishing already-draft catalog | Idempotent — 200 with no state change |
| Deleting all items from published catalog | Allowed — catalog stays published with 0 items (edge state) |

## Out of Scope

- Scheduled publish/unpublish
- Notify buyers when catalog is published

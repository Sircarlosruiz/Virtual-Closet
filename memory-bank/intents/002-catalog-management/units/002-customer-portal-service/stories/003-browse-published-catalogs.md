---
id: 003-browse-published-catalogs
unit: 002-customer-portal-service
intent: 002-catalog-management
status: draft
priority: must
created: 2026-05-28T00:00:00Z
assigned_bolt: 008-customer-portal-service
implemented: false
---

# Story: 003-browse-published-catalogs

## User Story

**As an** authenticated buyer
**I want** to browse my mayorista's published catalogs and view catalog items
**So that** I can review the garment collections shared with me

## Acceptance Criteria

- [ ] **Given** I have an active buyer session, **When** I GET `/api/portal/catalogs`, **Then** I receive a list of published catalogs from my mayorista only (`{ catalogs: [...], total, page }`)
- [ ] **Given** I GET `/api/portal/catalogs/{catalog_id}`, **When** the catalog is published and belongs to my mayorista, **Then** I receive the full catalog with items in mayorista-defined position order; each item includes `{ item_id, image_url (pre-signed), garment_name, price, cloth_type, sku }`
- [ ] **Given** I GET a catalog that is in `draft` status, **When** processed, **Then** I receive 404
- [ ] **Given** I GET a catalog that belongs to a different mayorista, **When** processed, **Then** I receive 403
- [ ] **Given** I am NOT authenticated (no buyer session), **When** I access any `/api/portal/*` endpoint, **Then** I receive 401

## Technical Notes

- `image_url` is a MinIO pre-signed URL generated at read time (15 min TTL) — not cached
- Items returned in ascending `position` order (mayorista-defined)
- Buyer cannot modify any catalog data — all portal endpoints are read-only
- Response must NOT leak draft catalog existence (404, not 403, for draft catalogs)

## Dependencies

### Requires
- 002-buyer-portal-auth (authenticated buyer session)
- 006-publish-unpublish-catalog in 001-catalog-service (published catalogs must exist)

### Enables
- 005-buyer-portal-page in 003-catalog-management-ui

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Mayorista has no published catalogs | `{ catalogs: [], total: 0 }` |
| Catalog is unpublished after buyer loads list | Detail request returns 404 |
| Direct access to catalog_id from another mayorista | 403 |

## Out of Scope

- Buyer favoriting or commenting on items
- Catalog search or filtering

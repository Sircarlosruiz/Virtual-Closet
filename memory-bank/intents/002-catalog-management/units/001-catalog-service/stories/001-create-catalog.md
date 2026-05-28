---
id: 001-create-catalog
unit: 001-catalog-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 006-catalog-service
implemented: true
---

# Story: 001-create-catalog

## User Story

**As a** mayorista
**I want** to create a named product catalog
**So that** I can organize my VTON-generated images into a shareable collection

## Acceptance Criteria

- [ ] **Given** I am authenticated, **When** I POST `/api/catalogs` with `{ name: "Summer 2026" }`, **Then** a catalog is created with `status: draft`, `item_count: 0`, and I receive `{ catalog_id, name, status, created_at }`
- [ ] **Given** I submit an empty or missing `name`, **When** the request is processed, **Then** I receive a 400 with validation error
- [ ] **Given** catalog is created, **When** I list my catalogs, **Then** the new catalog appears with `status: draft`
- [ ] **Given** I am NOT authenticated, **When** I POST `/api/catalogs`, **Then** I receive 401

## Technical Notes

- `mayorista_id` derived from JWT — not accepted as request body param
- `status` defaults to `draft` on creation — not settable at creation time
- `name` max length: 100 characters

## Dependencies

### Requires
- Platform JWT auth middleware (pre-existing platform infrastructure)

### Enables
- 002-add-catalog-item (need a catalog to add items to)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Name is only whitespace | 400 validation error |
| Name is 101 characters | 400 validation error |
| Duplicate catalog name for same mayorista | Allowed (names are not unique) |

## Out of Scope

- Setting status at creation time
- Catalog templates or defaults

---
id: 003-catalog-publish-flow
unit: 003-catalog-management-ui
intent: 002-catalog-management
status: draft
priority: must
created: 2026-05-28T00:00:00Z
assigned_bolt: 009-catalog-management-ui
implemented: false
---

# Story: 003-catalog-publish-flow

## User Story

**As a** mayorista
**I want** to publish or unpublish a catalog with a clear confirmation step
**So that** I control exactly when buyers can see my collection

## Acceptance Criteria

- [ ] **Given** I am on the catalog detail page with a draft catalog, **When** I click "Publish", **Then** a confirmation dialog appears summarizing the action
- [ ] **Given** I confirm publish, **When** the request succeeds, **Then** the status badge changes to "Published" immediately and a success toast appears
- [ ] **Given** the catalog has 0 items and I click "Publish", **When** I interact, **Then** the button is disabled with a tooltip "Add at least one item before publishing"
- [ ] **Given** I am on a published catalog, **When** I click "Unpublish", **Then** a confirmation dialog asks me to confirm and warns buyers will lose access
- [ ] **Given** I confirm unpublish, **When** the request succeeds, **Then** the status badge changes to "Draft"
- [ ] **Given** I click "Delete Catalog", **When** I confirm the destructive action, **Then** the catalog is deleted and I am redirected to the catalog list

## Technical Notes

- Publish/unpublish: PATCH `/api/catalogs/{id}` with `{ status }`
- Delete: DELETE `/api/catalogs/{id}` → redirect to list on success
- Publish button disabled state computed from `item_count === 0`

## Dependencies

### Requires
- 002-catalog-detail-page
- 006-publish-unpublish-catalog and 007-delete-catalog APIs

### Enables
- None (terminal catalog management action)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Publish API returns 422 (empty catalog race condition) | Show error: "Add items before publishing" |
| User closes confirmation dialog without confirming | No action taken |

## Out of Scope

- Scheduled publish/unpublish
- Sharing the publish link directly from this flow (handled in buyer portal flow)

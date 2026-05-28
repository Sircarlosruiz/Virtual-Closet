---
unit: 003-catalog-management-ui
intent: 002-catalog-management
phase: inception
status: ready
unit_type: frontend
default_bolt_type: simple-construction-bolt
created: 2026-05-28T00:00:00Z
updated: 2026-05-28T00:00:00Z
---

# Unit Brief: 003-catalog-management-ui

## Purpose

All user-facing interfaces for catalog management and buyer portal. Includes the mayorista's catalog dashboard, catalog detail/edit views, customer management page, and the buyer-facing portal where registered customers browse published catalogs.

## Scope

### In Scope
- Mayorista catalog dashboard (list all catalogs with status + item count)
- Catalog detail page (view items, add from VTON results, remove, reorder via drag-and-drop or arrows)
- Publish / unpublish flow with confirmation dialog
- Customer management page (register new customers, view registered customers)
- Buyer portal — authenticated customer browsing published catalog items

### Out of Scope
- Backend API logic (handled by 001-catalog-service and 002-customer-portal-service)
- VTON generation UI (handled by 003-vton-pipeline-ui in intent 001)
- PDF export

---

## Assigned Requirements

All user-facing FRs from FR-1 through FR-11 — this unit renders the UI that drives all catalog and buyer portal functionality.

---

## Domain Concepts

### Key Entities (from UI perspective)
| Entity | Rendered As |
|--------|-------------|
| Catalog | Card or row in dashboard; detail view with item grid |
| CatalogItem | Image card with metadata (name, price, cloth type, SKU) |
| Customer | Row in customer management table |
| Buyer session | Auth state — determines if portal renders or redirects to login |

### Key Operations (UI flows)
| Operation | UI Pattern |
|-----------|-----------|
| Create catalog | Modal form or inline input → POST /api/catalogs |
| Add item | Picker from completed VTON results → POST /api/catalogs/{id}/items |
| Reorder | Drag-and-drop or up/down arrows → PATCH .../reorder |
| Publish | Confirm dialog → PATCH .../status |
| Register customer | Form modal → POST /api/customers |
| Buyer auth | Token from URL → session cookie → portal renders |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 5 |
| Must Have | 5 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-catalog-list-page | Catalog Dashboard (Mayorista) | Must | Planned |
| 002-catalog-detail-page | Catalog Detail & Item Management | Must | Planned |
| 003-catalog-publish-flow | Publish / Unpublish Catalog Flow | Must | Planned |
| 004-customer-management-page | Customer Management Page | Must | Planned |
| 005-buyer-portal-page | Buyer Portal Catalog Browser | Must | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `001-catalog-service` | Catalog and item APIs |
| `002-customer-portal-service` | Customer registration and buyer portal APIs |

### Depended By
None.

### External Dependencies
None beyond backend API contracts.

---

## Technical Context

### Suggested Technology
- React + TypeScript (consistent with intent 001 frontend)
- React Query for server state (catalog and portal data)
- Existing component library / design system

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| catalog-service APIs | REST | JSON over HTTP |
| customer-portal APIs | REST | JSON over HTTP |

---

## Constraints

- Buyer portal routes use buyer session cookie — mayorista JWT is NOT valid for portal routes
- Image URLs are pre-signed (15 min TTL) — don't cache image URLs client-side across page loads
- Publish button must be disabled / show tooltip when catalog has 0 items

---

## Success Criteria

### Functional
- [ ] All 5 story acceptance criteria pass
- [ ] Mayorista can manage a full catalog lifecycle end-to-end
- [ ] Buyer can authenticate via link and browse a published catalog

### Non-Functional
- [ ] Catalog detail page loads within 2s on a standard connection
- [ ] Pre-signed image URLs fetched on page load (not cached stale)

### Quality
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 009-catalog-management-ui | simple-construction-bolt | 001, 002, 003 | Mayorista catalog pages |
| 010-catalog-management-ui | simple-construction-bolt | 004, 005 | Customer management + buyer portal |

---
id: 005-buyer-portal-page
unit: 003-catalog-management-ui
intent: 002-catalog-management
status: draft
priority: must
created: 2026-05-28T00:00:00Z
assigned_bolt: 010-catalog-management-ui
implemented: false
---

# Story: 005-buyer-portal-page

## User Story

**As a** registered buyer
**I want** to browse my mayorista's published catalogs through the buyer portal
**So that** I can view the garment collections shared with me

## Acceptance Criteria

- [ ] **Given** I open my invitation link, **When** the token is valid, **Then** I am authenticated and land on the buyer portal showing a list of published catalogs
- [ ] **Given** I click on a catalog, **When** it loads, **Then** I see the catalog name and a grid of items each showing: garment image, name, price, cloth type, and SKU
- [ ] **Given** I access the portal with an expired token, **When** processed, **Then** I see an error page with a "Request a new link" option
- [ ] **Given** I request a new link via email form, **When** submitted, **Then** I see a confirmation "Check your email for a new access link"
- [ ] **Given** the mayorista has no published catalogs, **When** I view the portal, **Then** I see an empty state "No collections available yet"

## Technical Notes

- Buyer portal is a distinct route (e.g., `/portal`) — mayorista nav is hidden
- Buyer session cookie managed separately from mayorista JWT
- Images load via pre-signed URLs returned by the API — no additional auth needed for image requests
- "Request new link" form: `POST /api/portal/magic-link` with `{ email }`
- Portal is read-only — no add/edit/delete controls rendered

## Dependencies

### Requires
- 002-buyer-portal-auth (authentication flow)
- 003-browse-published-catalogs API

### Enables
- None (terminal buyer journey)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Buyer session expires mid-session | API returns 401 → redirect to "Request new link" page |
| Catalog unpublished while buyer is viewing it | Next navigation or refresh returns empty/404 state |
| Image pre-signed URL expires during scroll | Browser shows broken image; next page load refreshes URLs |

## Out of Scope

- Buyer account settings or profile
- Favoriting or commenting on items
- Mobile-optimized responsive layout (nice-to-have, not in MVP scope)

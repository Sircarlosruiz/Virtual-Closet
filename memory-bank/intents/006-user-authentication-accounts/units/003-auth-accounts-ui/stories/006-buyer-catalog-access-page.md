---
id: 006-buyer-catalog-access-page
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
status: implemented
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: 035-auth-accounts-ui
implemented: true
---

# Story: 006-buyer-catalog-access-page

## User Story

**As a** buyer who received a catalog link
**I want** a landing page that validates my link and shows the shared catalogs
**So that** I can browse the mayorista's products without creating an account

## Acceptance Criteria

- [ ] **Given** I open `/catalog/access?token={jwt}`, **When** the page loads, **Then** the token is validated server-side (via API) and I am shown the accessible catalogs
- [ ] **Given** the token is valid, **When** the catalog list loads, **Then** I see only the catalogs specified in the token's `catalog_ids` — not all catalogs for the tenant
- [ ] **Given** the token has expired, **When** the page loads, **Then** I see "This link has expired. Please contact {mayorista name} for a new link."
- [ ] **Given** the token is invalid or tampered, **When** the page loads, **Then** I see "Invalid link. Please contact the sender for a new one."
- [ ] **Given** I am viewing catalogs as a buyer, **When** I inspect the page, **Then** there are no login prompts, no account creation CTAs, and no mayorista-specific controls visible

## Technical Notes

- Route: `/catalog/access` (public, no auth guard)
- Token passed as `?token=` query param
- Validation: call `POST /buyer-links/validate` on page load (server component or initial fetch)
- Buyer session is implicit (token in URL) — no cookie or localStorage
- Buyer view is read-only; no "try on" actions

## Dependencies

### Requires
- 005-validate-buyer-catalog-link (API)

### Enables
- None (leaf UI)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Token in URL is shared publicly/cached | Accepted risk — link expiry (30 days) limits exposure |
| Buyer bookmarks the URL after token expires | Sees expired link message with contact info |
| Mobile browser — token in URL | Works; no app required |

## Out of Scope

- Buyer trying on garments (future intent)
- Buyer placing orders (future intent)

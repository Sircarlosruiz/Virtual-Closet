---
id: 005-validate-buyer-catalog-link
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 005-validate-buyer-catalog-link

## User Story

**As a** buyer who received a catalog link
**I want** my link to be validated when I open it
**So that** I can access only the catalogs the mayorista shared with me, with no account required

## Acceptance Criteria

- [ ] **Given** a valid, unexpired buyer JWT, **When** `POST /buyer-links/validate` is called, **Then** I receive `{ tenant_id, catalog_ids[], valid: true }` — no DB lookup required
- [ ] **Given** an expired buyer JWT, **When** validation is attempted, **Then** the response is `{ valid: false, reason: "link_expired" }` with a 200 status (not 401 — buyer has no session to refresh)
- [ ] **Given** a tampered or malformed JWT, **When** validation is attempted, **Then** `{ valid: false, reason: "invalid_token" }` with a 200 status
- [ ] **Given** a JWT signed with the wrong tenant secret, **When** validation is attempted, **Then** `{ valid: false, reason: "invalid_token" }`
- [ ] **Given** a valid buyer token, **When** the buyer tries to access a catalog endpoint not in their `catalog_ids`, **Then** `403 Forbidden` is returned by the catalog service

## Technical Notes

- Validation is fully stateless — JWT decoded with tenant's `buyer_link_secret` fetched via `tenant_id` in unverified token header
- Two-step validation: (1) decode without verification to extract `tenant_id`, (2) fetch `buyer_link_secret` from DB, (3) verify signature
- Endpoint: `POST /buyer-links/validate` — public (no mayorista JWT required)
- Buyer requests use a separate FastAPI dependency (`get_buyer_context`) that does NOT enforce `tenant_id` from JWT claims

## Dependencies

### Requires
- 004-generate-buyer-catalog-link

### Enables
- Frontend buyer access page (003-auth-accounts-ui story 006)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant has been deactivated after link was issued | Fetch `buyer_link_secret` fails → `invalid_token` |
| `tenant_id` in token doesn't exist in DB | `invalid_token` (don't reveal tenant non-existence) |
| Buyer accesses link on mobile browser | Same stateless validation; no cookies or sessions needed |

## Out of Scope

- Single-use buyer links (would require stateful tracking — future intent)
- Analytics on buyer link access (future intent)

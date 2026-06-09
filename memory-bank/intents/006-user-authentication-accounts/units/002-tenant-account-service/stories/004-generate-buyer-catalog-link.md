---
id: 004-generate-buyer-catalog-link
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
status: draft
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 004-generate-buyer-catalog-link

## User Story

**As a** mayorista
**I want** to generate a shareable link that grants a buyer read-only access to specific catalogs
**So that** my buyers can browse my published catalogs without creating an account

## Acceptance Criteria

- [ ] **Given** I am authenticated and own catalog IDs C1 and C2, **When** I call `POST /buyer-links` with `{ catalog_ids: [C1, C2], ttl_days: 30 }`, **Then** I receive a signed JWT URL and the link is recorded in `BuyerLink` for audit purposes
- [ ] **Given** I request a link for a catalog that belongs to another tenant, **When** the request is processed, **Then** a 404 is returned (cross-tenant isolation applies)
- [ ] **Given** `ttl_days` is not provided, **When** the link is generated, **Then** the default TTL of 30 days is applied
- [ ] **Given** I call `GET /buyer-links`, **When** the request is processed, **Then** I receive a list of all links I have generated for my tenant, including their expiry and catalog scope
- [ ] **Given** a buyer link is generated, **When** inspecting the JWT payload, **Then** it contains `{ tenant_id, catalog_ids[], exp, jti, type: "buyer" }` — no user data

## Technical Notes

- Buyer link JWT: HS256, signed with `Tenant.buyer_link_secret`
- JWT payload: `{ sub: "buyer", tenant_id, catalog_ids, jti, iat, exp }`
- `BuyerLink` table is an audit trail only; validation is stateless (no DB lookup during access)
- Endpoint: `POST /buyer-links` (requires mayorista JWT)
- List endpoint: `GET /buyer-links` (returns all links for tenant)
- Generated URL format: `{FRONTEND_URL}/catalog/access?token={jwt}`

## Dependencies

### Requires
- 001-create-manage-tenant (needs `buyer_link_secret` on tenant)

### Enables
- 005-validate-buyer-catalog-link

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `catalog_ids` list is empty | Validation error: must specify at least one catalog |
| `ttl_days` > 365 | Capped at 365 days |
| Catalog is unpublished when link is accessed | Buyer sees catalog but items may be limited (catalog service enforces publish state) |

## Out of Scope

- Revoking individual buyer links before expiry (future intent — would require stateful validation)
- Restricting buyer access to specific items within a catalog

---
id: 003-cross-tenant-access-returns-404
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 003-cross-tenant-access-returns-404

## User Story

**As a** platform security system
**I want** cross-tenant resource access attempts to return 404 (not 403)
**So that** the existence of other tenants' resources is not revealed to attackers

## Acceptance Criteria

- [ ] **Given** mayorista A is authenticated, **When** they request a resource (media, catalog, job) that belongs to mayorista B's tenant, **Then** the response is `404 Not Found` — identical to if the resource didn't exist
- [ ] **Given** a valid JWT with `tenant_id = A`, **When** any tenant-scoped query is executed, **Then** the ORM filter ensures the result set only contains records where `tenant_id = A`; the 404 arises naturally from an empty result
- [ ] **Given** an integration test, **When** a resource is created under tenant A and fetched using tenant B's credentials, **Then** the test asserts a 404 response
- [ ] **Given** a bulk endpoint (e.g., list all media), **When** called by tenant A, **Then** results contain only tenant A's records — no records from other tenants leak into paginated results

## Technical Notes

- 404 behavior emerges naturally from the ORM filter — no explicit cross-tenant check needed
- Integration tests should cover: GET /media/{id}, GET /catalogs/{id}, GET /vton-jobs/{id}, GET /batch-jobs/{id}
- No 403 should be returned for cross-tenant resource access (to prevent enumeration)
- Document this pattern in `memory-bank/standards/` decision index once constructed

## Dependencies

### Requires
- 002-tenant-isolation-middleware

### Enables
- None (security validation)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant A knows the exact UUID of tenant B's catalog | Still returns 404 — UUID knowledge provides no access |
| Admin role within tenant A tries to access tenant B | Still 404 — admin is scoped to their own tenant |

## Out of Scope

- Super-admin cross-tenant access (future intent)
- Audit logging of cross-tenant access attempts (future intent)

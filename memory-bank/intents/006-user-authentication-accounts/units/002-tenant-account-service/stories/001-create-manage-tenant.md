---
id: 001-create-manage-tenant
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 001-create-manage-tenant

## User Story

**As a** platform system
**I want** to automatically create a tenant when a mayorista registers
**So that** all their data is isolated within their own organizational boundary

## Acceptance Criteria

- [ ] **Given** a mayorista completes registration, **When** the user record is created, **Then** a `Tenant` record is created atomically in the same transaction with a unique UUID, the mayorista's business name, and a generated `buyer_link_secret` (32-byte random hex)
- [ ] **Given** a tenant exists, **When** the mayorista updates their business name via `PATCH /tenants/me`, **Then** the `Tenant.name` is updated and `updated_at` is refreshed
- [ ] **Given** a tenant is fetched via `GET /tenants/me`, **When** the request includes a valid JWT, **Then** only the requesting mayorista's tenant data is returned
- [ ] **Given** a mayorista's tenant is created, **When** inspecting the user record, **Then** `user.tenant_id` is set to the new tenant's UUID

## Technical Notes

- Tenant creation is atomic with user creation (single DB transaction)
- `buyer_link_secret`: `secrets.token_hex(32)` — generated at creation, never exposed in API responses
- `Tenant` model fields: `id` (UUID), `name`, `slug` (unique, kebab-case from name), `buyer_link_secret`, `settings` (JSONB default `{}`), `created_at`, `updated_at`, `is_active`
- Endpoints: `GET /tenants/me`, `PATCH /tenants/me`

## Dependencies

### Requires
- None (foundational)

### Enables
- All other stories in this unit
- `001-auth-service` Story 001 (mayorista-registration)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Business name collision (same slug) | Append numeric suffix to slug (`my-store-2`) |
| Transaction rollback on tenant creation | User not created either; full rollback |

## Out of Scope

- Tenant deletion (admin operation, future intent)
- Multi-user tenants at creation time (admins added separately via story 006)

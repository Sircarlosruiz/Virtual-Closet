---
id: 002-tenant-isolation-middleware
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 002-tenant-isolation-middleware

## User Story

**As a** platform system
**I want** all database queries to be automatically scoped to the requesting mayorista's tenant
**So that** no mayorista can accidentally or maliciously access another's data

## Acceptance Criteria

- [ ] **Given** any authenticated API request, **When** the request is processed, **Then** `tenant_id` is extracted from the JWT claims and injected into all DB queries as a filter condition
- [ ] **Given** a JWT with a valid `tenant_id`, **When** a query runs against any tenant-scoped table, **Then** the query includes `WHERE tenant_id = :tenant_id` enforced at the repository/ORM layer — not optional
- [ ] **Given** the Alembic migration runs, **When** it completes, **Then** all platform tables (`media`, `catalogs`, `vton_jobs`, `batch_jobs`) have a `tenant_id` UUID column with a NOT NULL FK constraint to `tenants.id`
- [ ] **Given** existing platform records before migration, **When** the migration runs, **Then** all existing rows are backfilled with a default "system" tenant (migration is non-destructive)
- [ ] **Given** a request with no JWT (unauthenticated), **When** the middleware runs, **Then** a 401 is returned before any DB query executes

## Technical Notes

- Middleware implemented as a FastAPI dependency injected at router level, not globally (buyer routes are exempt)
- Alembic migration strategy: 3-step — (1) add nullable `tenant_id`, (2) backfill existing rows with default tenant UUID, (3) add NOT NULL constraint + FK
- ORM approach: SQLAlchemy session wrapper that automatically appends `filter(Model.tenant_id == tenant_id)` to all queries
- Tables to migrate: `media`, `catalogs`, `vton_jobs`, `batch_jobs` (and any future tables)

## Dependencies

### Requires
- 001-create-manage-tenant

### Enables
- 003-cross-tenant-access-returns-404
- All platform features (isolation is a prerequisite)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Migration with large existing dataset | Backfill in batches of 1000 rows to avoid lock contention |
| Missing `tenant_id` in JWT (malformed token) | 401 — token rejected before middleware runs |
| Service-to-service calls without user JWT | Separate service account flow (out of scope; use a bypass flag for internal services) |

## Out of Scope

- Row-Level Security (RLS) at PostgreSQL level (could be added as defense-in-depth later)
- Cross-tenant admin operations (future intent)

---
id: 028-tenant-account-service
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
type: ddd-construction-bolt
status: complete
stories:
  - 001-create-manage-tenant
  - 002-tenant-isolation-middleware
  - 003-cross-tenant-access-returns-404
created: 2026-06-08T00:00:00.000Z
started: 2026-06-09T00:00:00.000Z
completed: "2026-06-09T19:24:51Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-06-09T00:00:00.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-06-09T00:00:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-06-09T00:00:00.000Z
    artifact: adr-012-tenant-isolation-strategy.md, adr-013-alembic-migration-strategy.md, adr-014-stateless-buyer-link-validation.md, adr-015-rls-deferred.md
  - name: implement
    completed: 2026-06-09T00:00:00.000Z
    artifact: source code
  - name: test
    completed: 2026-06-09T00:00:00.000Z
    artifact: ddd-03-test-report.md
requires_bolts: []
enables_bolts:
  - 029-tenant-account-service
  - 030-auth-service
requires_units: []
blocks: false
complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 1
  testing_scope: 3
---

## Bolt: 028-tenant-account-service

### Objective

Introduce multi-tenancy to the Virtual Closet platform. Create the `Tenant` model, run the Alembic migration that adds `tenant_id` to all platform tables (with backfill), and implement the FastAPI tenant isolation middleware that scopes all DB queries to the requesting mayorista's tenant.

### Stories Included

- [ ] **001-create-manage-tenant**: Create and Manage Tenant — Priority: Must
- [ ] **002-tenant-isolation-middleware**: Tenant Isolation Middleware + Alembic Migration — Priority: Must
- [ ] **003-cross-tenant-access-returns-404**: Cross-Tenant Access Returns 404 — Priority: Must

### Expected Outputs

- `Tenant` SQLAlchemy model + Alembic migration (create tenants table + backfill + FK constraints)
- `tenant_id` column added to: `media`, `catalogs`, `vton_jobs`, `batch_jobs`
- `TenantContext` FastAPI dependency (injected at router level)
- `GET /tenants/me`, `PATCH /tenants/me` endpoints
- Integration tests: cross-tenant isolation for all major entity types

### Dependencies

#### Bolt Dependencies (within intent)
- None (foundational bolt)

#### Unit Dependencies (cross-unit)
- None

#### Enables (other bolts waiting on this)
- 029-tenant-account-service (buyer links + admin roles need tenant model)
- 030-auth-service (user registration needs tenant creation)

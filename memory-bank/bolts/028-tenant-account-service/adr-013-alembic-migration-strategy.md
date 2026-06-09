---
bolt: 028-tenant-account-service
created: 2026-06-09T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-013: Multi-Step Alembic Migration with Default Tenant Backfill

## Context

The platform has existing data in `media`, `catalogs`, `vton_jobs`, `batch_jobs`, and `users` tables with no `tenant_id` column. Introducing multi-tenancy requires adding `tenant_id` to all these tables and ensuring every existing row is associated with a tenant. The migration must be safe, reversible, and complete within a reasonable time window (< 60s).

## Decision

Execute a 7-step Alembic migration within a single transaction:

1. Create `tenants` table
2. Insert a default tenant (`id = 00000000-0000-0000-0000-000000000001`, slug = "default")
3. Add nullable `tenant_id` column to each platform table
4. Backfill: set `tenant_id = default_tenant_id` for all existing rows
5. Add NOT NULL constraint on `tenant_id` columns
6. Add FK constraints referencing `tenants(id)`
7. Add indexes on `tenant_id` for query performance

The migration runs in a single transaction. If any step fails, the entire migration rolls back.

## Rationale

Adding `tenant_id` as NOT NULL from the start would fail because existing rows have no tenant. A multi-step approach allows us to: (a) create the tenant first, (b) add the column as nullable, (c) backfill, (d) then enforce the constraint. Using a default tenant is simpler than trying to infer tenant ownership from existing data.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Single-step migration with default value | Simpler | Doesn't work with FK constraints; can't backfill properly | FK requires the referenced row to exist first |
| Per-table migrations | Easier to rollback individual tables | Inconsistent state if some succeed and others fail | All-or-nothing is safer for multi-tenancy |
| Application-level backfill script | More control over batching, progress reporting | More complex; requires running separate script after migration | Overkill for current data volume (< 60s estimated) |
| Create tenant per existing user | More accurate tenant mapping | Requires complex logic to infer ownership; may create orphan tenants | Default tenant is safer; tenants can be reassigned later |

## Consequences

### Positive

- Atomic: single transaction ensures all-or-nothing
- Safe: rollback on any failure
- Simple: default tenant approach avoids complex inference logic
- Documented: rollback plan in migration comments

### Negative

- All existing data belongs to one default tenant initially
- Mayoristas with existing data will need to be migrated to their own tenants (separate process)
- Migration locks tables during execution (acceptable for < 60s window)

### Risks

- **Risk**: Migration timeout on large datasets. **Mitigation**: Add progress logging; if data volume grows, switch to batched backfill with explicit commits per batch (requires removing transaction wrapper for backfill steps).
- **Risk**: FK constraint failure if default tenant is deleted. **Mitigation**: Add database-level trigger or application-level guard preventing deletion of the default tenant.

## Related

- **Stories**: 002-tenant-isolation-middleware
- **Standards**: Should be referenced in deployment runbook
- **Previous ADRs**: None

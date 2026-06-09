---
bolt: 028-tenant-account-service
created: 2026-06-09T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-012: Multi-Layer Tenant Isolation Enforcement

## Context

The Virtual Closet platform is introducing multi-tenancy. Every query must be scoped to the current tenant's `tenant_id` to prevent cross-tenant data leaks. We need a strategy that is both developer-friendly (hard to forget) and secure (defense-in-depth).

## Decision

Implement tenant isolation at two layers:

1. **Primary**: FastAPI `TenantContext` dependency injected at the router level. Every protected route receives `tenant_id` from the JWT and passes it to service methods.
2. **Secondary**: SQLAlchemy `before_compile` event listener that auto-appends `tenant_id` filters to queries as a safety net.

Both layers must agree — if the dependency injection fails to provide a tenant_id, the request is rejected before reaching the ORM.

## Rationale

Relying on a single layer is risky. Developers might forget to pass `tenant_id` to a service method, or a new router might be added without the dependency. The ORM-level listener catches these mistakes before they become data leaks.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Dependency injection only | Simple, explicit, easy to test | Easy to forget; single point of failure | Not enough safety for production multi-tenancy |
| ORM listener only | Automatic, no developer action needed | Hard to debug; implicit behavior; affects all queries | Too magical; makes testing harder |
| Postgres RLS only | Database-enforced, foolproof | Complex setup; debugging is hard; not all ORMs play well with RLS | Deferred to future hardening (see ADR-015) |
| No isolation (shared schema, no filtering) | Simplest | Data leaks guaranteed | Not acceptable |

## Consequences

### Positive

- Defense-in-depth: two independent layers must both fail for a leak to occur
- Developer experience: explicit `TenantContext` makes tenant scoping visible in code
- Testability: both layers can be tested independently
- ORM listener catches regressions in new code

### Negative

- Slightly more complex architecture
- ORM listener adds minimal overhead to every query (< 1ms)
- Two layers to maintain and document

### Risks

- **Risk**: ORM listener might interfere with admin-level queries that need cross-tenant access. **Mitigation**: Provide an `override_tenant_filter` context manager for admin operations that explicitly bypass the filter (logged and audited).

## Related

- **Stories**: 002-tenant-isolation-middleware, 003-cross-tenant-access-returns-404
- **Standards**: Should be added to coding-standards.md under "Multi-tenancy"
- **Previous ADRs**: ADR-001 (Separate Buyer Authentication Context)

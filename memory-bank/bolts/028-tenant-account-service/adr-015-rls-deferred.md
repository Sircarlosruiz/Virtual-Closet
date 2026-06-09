---
bolt: 028-tenant-account-service
created: 2026-06-09T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-015: Postgres RLS Deferred as Future Defense-in-Depth

## Context

PostgreSQL Row Level Security (RLS) provides database-enforced row-level access control. It would be the strongest possible tenant isolation mechanism, as it operates at the database engine level and cannot be bypassed by application bugs. However, implementing RLS adds complexity to the migration, ORM configuration, and debugging experience.

## Decision

Do NOT implement Postgres RLS in this bolt. Rely on application-level tenant isolation (FastAPI dependency + SQLAlchemy event listener) for the initial multi-tenancy release. Recommend RLS as a future hardening step to be evaluated after the initial release is stable.

RLS should be revisited when:
- The platform has multiple tenants in production
- Security audit requires database-level isolation
- ORM-level filtering proves insufficient (e.g., edge cases, raw SQL queries)

## Rationale

The application-level approach provides strong isolation with two defense layers (ADR-012). Adding RLS would significantly increase migration complexity, require SQLAlchemy dialect-specific configuration, and make debugging more difficult. The incremental security benefit does not justify the implementation cost for the initial release.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Implement RLS now | Strongest isolation; database-enforced; cannot be bypassed by app bugs | Complex migration; SQLAlchemy RLS support is limited; hard to debug; affects all queries | Too much complexity for initial release |
| RLS on critical tables only | Focused protection on sensitive data | Inconsistent security model; confusing for developers | Partial protection creates false sense of security |
| Skip RLS entirely | Simplest approach | No database-level safety net | Rejected as future recommendation; should be evaluated later |

## Consequences

### Positive

- Faster initial delivery
- Simpler migration (no RLS policy setup)
- Easier debugging and testing
- ORM-level approach is well-understood by the team

### Negative

- No database-level safety net if application-level filtering fails
- Raw SQL queries (if any) are not automatically scoped
- Future RLS implementation will require migration of existing policies

### Risks

- **Risk**: Application-level filtering has a bug that leaks cross-tenant data. **Mitigation**: Comprehensive integration tests for cross-tenant isolation (required by this bolt's test stage); code review focused on tenant scoping; monitoring for anomalous query patterns.
- **Risk**: Future RLS implementation is disruptive. **Mitigation**: Design application-level code to be RLS-compatible (always pass tenant_id, never rely on application-only filtering).

## Related

- **Stories**: 002-tenant-isolation-middleware, 003-cross-tenant-access-returns-404
- **Standards**: Should be noted in system-architecture.md under "Future Hardening"
- **Previous ADRs**: ADR-012 (Multi-Layer Tenant Isolation Enforcement)

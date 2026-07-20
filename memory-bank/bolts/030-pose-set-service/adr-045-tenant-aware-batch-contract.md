---
bolt: 030-pose-set-service
created: 2026-07-18T06:47:24Z
status: accepted
superseded_by: null
---

# ADR-045: Pass Tenant Context Through Internal Batch Submission

## Context

Current platform migrations make `BatchJob.tenant_id` non-nullable, while the
existing batch submission service primarily accepts `mayorista_id`. PoseSet
must call that service internally and persist a valid BatchJob without creating
a parallel batch path.

## Decision

Extend the existing batch submission contract with the authenticated
`tenant_id`. Both the public batch router and PoseSet service pass the tenant
from the authenticated mayorista context, and BatchJob creation sets it. The
PoseSet table also stores the same tenant ID for defense-in-depth scoping.
No independent tenant inference or default tenant is introduced in PoseSet.

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Infer tenant from a database query inside batch service | Fewer caller changes | Hidden lookup and possible cross-tenant ambiguity | Explicit context is safer and matches current auth design |
| Make BatchJob.tenant_id nullable | Backwards-compatible signature | Weakens tenant isolation and conflicts with current schema | Not acceptable for new submissions |
| Add tenant-aware parameter (chosen) | Explicit, minimal, reusable for all callers | Requires updating existing call sites | Preserves current tenancy guarantees |

## Consequences

### Positive

- PoseSet and existing batch submissions satisfy the non-null tenant FK
- Tenant scoping is explicit at the service boundary
- No duplicated BatchJob/BatchItem logic

### Negative

- Existing batch router and service signatures require a coordinated change
- Legacy tests and callers must provide tenant context or use a test fixture

### Risks

- Existing users without a tenant ID cannot submit new batches. Mitigation: keep
  the existing authentication migration/backfill as a prerequisite and fail
  clearly before creating records.

## Related

- **Stories**: 001-submit-pose-set
- **Previous ADRs**: ADR-012, ADR-013, ADR-039, ADR-040

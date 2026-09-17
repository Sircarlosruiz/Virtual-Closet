---
bolt: 044-generation-reliability
created: 2026-09-17T17:10:00Z
status: proposed
superseded_by: null
---

# ADR-050: Atomic Postgres Column for the Per-Job Concurrency Lease

## Context

Preventing a duplicate queue delivery from starting a second concurrent
provider call for the same job requires a mutual-exclusion mechanism. The
project already uses Redis for several ephemeral, cross-instance
coordination needs (session denylists in ADR-016/023/027, and it is the
established pattern for locks and TTL-based state). A concurrency lease for
a generation job is a similarly ephemeral, cross-worker coordination
problem, so Redis is the default candidate.

## Decision

Implement the concurrency lease as an atomic conditional `UPDATE` on a
`lock_token`/`locked_at` pair of columns on `generation_jobs`
(`UPDATE ... SET lock_token = :token WHERE id = :job_id AND lock_token IS
NULL`), following the same atomic-`UPDATE`-expression pattern already used
for batch counters (ADR-009, ADR-021), rather than introducing a Redis-based
lock for this case.

## Rationale

The lease is scoped to exactly one row that already lives in Postgres and is
already the transactional source of truth for the job. Postgres's
row-level locking and conditional `UPDATE` give the same
fail-closed, single-writer guarantee as a Redis `SETNX` lock, without adding
a second system that must be consistent with the job row's own state (a
Redis-based lease could theoretically be held while the Postgres row says
something different, requiring reconciliation between two stores).

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Redis `SETNX` lock keyed by job ID (matches existing project pattern) | Consistent with ADR-016/023/027 precedent; fast | Adds a second source of truth that must stay consistent with the Postgres job row; another failure mode to reason about (Redis unavailable vs Postgres unavailable) | Unnecessary given the lease is 1:1 with a row Postgres already owns |
| Postgres `SELECT ... FOR UPDATE` held for the duration of the provider call | No extra columns needed | Holds a transaction open for the full duration of an external HTTP call to OpenAI, risking connection pool exhaustion | Long-held transactions across external I/O are unsafe |
| Atomic conditional `UPDATE` on `lock_token` columns (selected) | Single source of truth, fail-closed, no long-held transaction, reuses an established project pattern | Requires explicit release on completion/failure paths | Selected |

## Consequences

### Positive

- No new infrastructure dependency introduced for this feature.
- Lease state can never disagree with the job row it protects, since it is
  the same row.
- Reuses a pattern already reviewed and accepted in this codebase.

### Negative

- If a worker crashes after acquiring the lease but before releasing it, the
  lease remains held until an operator or a future reconciliation process
  clears it — Redis TTL-based locks would self-expire.

### Risks

- Orphaned leases from crashed workers block further attempts on that job.
  Mitigation: this is scoped as a known limitation for this bolt; a
  future reconciliation pass (already anticipated by ADR-048) should clear
  stale leases older than the worker's maximum expected task duration.

## Related

- **Stories**: 004-retry-idempotency-limits
- **Standards**: `memory-bank/standards/system-architecture.md`
- **Previous ADRs**: ADR-009, ADR-016, ADR-021, ADR-023, ADR-027, ADR-036, ADR-048

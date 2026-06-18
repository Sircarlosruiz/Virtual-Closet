---
adr: 037
title: "Migration Job backoffLimit: 0 — Fail Fast, No Auto-Retry"
status: accepted
bolt: 041-database-migrations
created: 2026-06-18T16:20:00Z
read_when:
  - Configuring a k8s Job that runs database migrations
  - Deciding retry policy for any batch Job that modifies shared persistent state
  - Debugging a failed migration Job
---

## Context

The Alembic migration Job (`k8s/staging/migrations/job.yaml`) runs `alembic upgrade head` as part of every staging deployment. It runs once per image tag, completes in seconds, and directly modifies the PostgreSQL schema — a shared, persistent resource.

The default `backoffLimit` for a k8s Job is `6`. With `backoffLimit: N`, Kubernetes automatically creates up to N+1 Pod attempts if previous Pods exit non-zero. Each new Pod starts from the same container spec with no knowledge of what the previous Pod may have partially done.

## Problem

Alembic migrations are not fully idempotent under failure. Specifically:

1. **Partial-transaction failure**: Alembic wraps each revision's `upgrade()` in a single database transaction. If the DB crashes mid-transaction, PostgreSQL rolls back the entire revision cleanly — this case is safe to retry.

2. **Post-commit DDL failure**: Some DDL operations (e.g., `CREATE INDEX CONCURRENTLY`) are not transactional. If the process is killed after the DDL succeeds but before alembic updates the `alembic_version` table, the next attempt will try to apply the same DDL again (e.g., `CREATE INDEX`) and fail with `already exists` — a different, confusing error from a different code path.

3. **Schema partially applied**: If a migration runs multiple DDL statements and fails mid-way through a revision with partial success (Alembic does not guarantee all-or-nothing at the revision granularity for non-transactional DDL), retrying may attempt operations already completed.

In all three cases, auto-retry produces a pod that fails with a misleading error, making diagnosis harder and potentially leaving the schema in an unexpected state.

## Decision

Set `backoffLimit: 0` on the migration Job.

When a migration Pod exits non-zero:
- Kubernetes marks the Job as `Failed` immediately.
- No additional Pods are created.
- The pipeline (`kubectl wait --for=condition=complete --timeout=300s`) receives a non-zero exit code and halts.
- The operator reads `kubectl logs job/alembic-migrate-{SHA} -n virtual-closet-staging` to diagnose the actual failure.
- After inspecting the DB state, the operator decides: retry the same Job, apply a fixup migration, or roll back.

## Consequences

**Positive:**
- Migration failure is immediately visible in CI logs with the actual error, not a secondary `already exists` error.
- Operator is forced to understand the DB state before retrying — prevents compounding failures.
- Pod stays in `Failed` state with logs accessible until TTL (`ttlSecondsAfterFinished: 3600`).

**Negative:**
- Transient failures (e.g., brief network partition to PostgreSQL) will halt the pipeline rather than self-healing. Operators must manually re-trigger the deployment.
- Operational burden: every migration failure requires human investigation.

**Mitigation for transient failures**: The alembic connection will retry internally (SQLAlchemy connection pool retry). `activeDeadlineSeconds: 300` gives 5 minutes of retry window at the connection level before the Job itself times out.

## Alternatives Considered

| Alternative | Rejected because |
|-------------|-----------------|
| `backoffLimit: 3` (default-like) | Auto-retry on partial DDL failure produces misleading error; harder to debug |
| `backoffLimit: 1` | Same issue — even one retry is risky for non-transactional DDL |
| Ensure all DDL is transactional | PostgreSQL DDL IS transactional (unlike MySQL); this would work for standard Alembic ops. However, `CREATE INDEX CONCURRENTLY` is an explicit exception the team may use in future, and `backoffLimit: 0` is the safer general policy. |
| Pre-flight idempotency check | Would require a custom wrapper script; adds complexity; `backoffLimit: 0` achieves the same safety with zero additional code. |

## Applies To

- `k8s/staging/migrations/job.yaml`
- `k8s/staging/migrations/rollback-job.yaml.template`
- Any future environment's migration Job (production, preview)

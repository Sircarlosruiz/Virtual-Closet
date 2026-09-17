---
bolt: 043-image-generation-service
created: 2026-09-17T04:07:47Z
status: proposed
---

# ADR-048: Commit Generation Jobs Before Queue Publication

## Context

Generation requests need a durable job ID immediately, while inference must be
asynchronous. Publishing a Celery task before the database transaction commits
can create a task whose job row does not exist. Publishing after commit can
instead leave a durable queued job if the broker is unavailable.

## Decision

Create and commit the `queued` `GenerationJob` first, then publish a Celery task
containing only its UUID. Queue publication remains injectable for tests and a
future reconciliation mechanism can recover jobs that were committed but not
published.

## Rationale

Database durability is the source of truth for job state. This ordering avoids
orphaned worker tasks and gives callers a stable identifier even when queue
publication requires recovery.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Publish before database commit | Worker can start immediately | Worker may observe no job after rollback | Rejected |
| Require a distributed transaction | Strong cross-system atomicity | Operationally complex and unsupported by Celery/RabbitMQ | Rejected |
| Commit then publish with reconciliation | Simple durable boundary | Requires recovery for publish failures | Selected |

## Consequences

### Positive

- Every published task references a durable job.
- API response can return a stable queued job ID.

### Negative

- Broker failure can leave queued jobs requiring reconciliation.
- The worker may start slightly after the API transaction completes.

### Risks

- Reconciliation must avoid duplicate processing once reliability features are
  added. Use the reliability bolt's idempotency controls for recovery attempts.

## Related

- **Stories**: 002-staff-generation-jobs
- **Standards**: `memory-bank/standards/system-architecture.md`
- **Previous ADRs**: ADR-005, ADR-007

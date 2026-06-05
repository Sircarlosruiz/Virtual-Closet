---
bolt: 024-batch-job-service
created: 2026-06-04T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-009: Atomic Counter Updates via SQLAlchemy F() Expressions

## Context

When multiple `VtonJob` tasks complete concurrently (e.g., a 100-item batch where many items finish around the same time), multiple Celery workers will attempt to update `BatchJob.completed_count` or `BatchJob.failed_count` simultaneously. A naive `SELECT → increment → UPDATE` pattern is vulnerable to lost updates:

```
Worker A: SELECT completed_count = 5
Worker B: SELECT completed_count = 5
Worker A: UPDATE completed_count = 6
Worker B: UPDATE completed_count = 6  ← Lost update! Should be 7
```

We need a concurrency-safe strategy for counter updates that works with PostgreSQL and SQLAlchemy async.

## Decision

Use **SQLAlchemy `UPDATE ... SET count = count + 1` with `RETURNING`** for all counter updates. This is a single atomic SQL statement that PostgreSQL executes with row-level locking:

```python
from sqlalchemy import update

async def increment_completed_count(self, batch_id: uuid.UUID):
    stmt = (
        update(BatchJob)
        .where(BatchJob.id == batch_id)
        .values(completed_count=BatchJob.completed_count + 1)
        .returning(BatchJob.completed_count, BatchJob.failed_count, BatchJob.total_items)
    )
    result = await self._db.execute(stmt)
    row = result.first()
    return row.completed_count, row.failed_count, row.total_items
```

PostgreSQL acquires a row-level lock during the `UPDATE`, so concurrent updates are serialized at the database level. The `RETURNING` clause provides the new counter values in a single round-trip, enabling the caller to determine if the batch has reached terminal state.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **`SELECT FOR UPDATE` then increment** | Explicit locking; can read current values before update | Two round-trips (SELECT + UPDATE); higher lock contention; more code | Unnecessary complexity — single `UPDATE` is sufficient and faster |
| **Optimistic locking with version column** | No row-level locks; detects conflicts via version mismatch | Requires retry logic on conflict; adds `version` column to schema; more complex code | Overkill for simple counter increments; PostgreSQL row-level locking is simpler |
| **PostgreSQL `SKIP LOCKED`** | Non-blocking; skips locked rows | Loses updates if row is locked; not suitable for counter increments | Wrong semantics — we need every increment to be applied |
| **`UPDATE ... SET count = count + 1`** (chosen) | Single atomic statement; PostgreSQL handles locking; no retry logic needed; `RETURNING` provides new values | Requires PostgreSQL (not portable to all databases) | Best trade-off: simple, correct, performant; we already use PostgreSQL |

## Consequences

### Positive

- **No lost updates**: PostgreSQL row-level locking guarantees every increment is applied
- **Single round-trip**: `UPDATE ... RETURNING` combines write and read in one query
- **No retry logic needed**: Database handles serialization; no application-level conflict resolution
- **Simple code**: One SQL statement, no version columns, no explicit locking
- **Works with async**: Compatible with SQLAlchemy async session

### Negative

- PostgreSQL-specific — not portable to MySQL/SQLite (not a concern for this project)
- Row-level lock contention under extreme concurrency (100+ simultaneous completions for same batch) — but this is acceptable for our scale

### Risks

- **Deadlock**: Unlikely with single-row updates, but if multiple tables are updated in different orders, deadlock could occur. Mitigation: always update `BatchJob` first, then `BatchItem` — consistent ordering prevents deadlocks.
- **Long-running transaction holding lock**: If the callback transaction is slow, other workers wait. Mitigation: keep callback transaction short — only counter updates, no external API calls.

## Related

- **Stories**: 003-track-item-status, 004-partial-failure-isolation
- **Standards**: Should be added to coding-standards.md under "Concurrent counter updates"
- **Previous ADRs**: ADR-005 (transactional Celery publishing)

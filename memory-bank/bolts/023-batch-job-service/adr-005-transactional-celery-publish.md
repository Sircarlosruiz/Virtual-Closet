---
bolt: 023-batch-job-service
created: 2026-06-04T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-005: Use SQLAlchemy transaction.on_commit for Celery Task Publishing

## Context

The batch submission flow requires atomic creation of `BatchJob` + `BatchItem` records and enqueueing of individual `VtonJob` Celery tasks. Celery task publishing (`task.delay()`) is not transactional with PostgreSQL — it sends a message to RabbitMQ immediately. If the database transaction fails after tasks are published (e.g., constraint violation, connection error), orphaned Celery tasks will execute against non-existent `VtonJob` records, causing errors and inconsistent state.

This is a distributed transaction problem: we need to coordinate a database write with an external message broker.

## Decision

Use SQLAlchemy's `session.connection().connection` event or `sqlalchemy.event.listen` with `after_commit` to defer Celery task publishing until **after** the database transaction successfully commits. Specifically, use `sqlalchemy.orm.SessionEvents.after_commit` or collect tasks in a list and publish them after `session.commit()` succeeds.

Implementation pattern:
```python
async with session.begin():
    # 1. Create BatchJob + BatchItem records
    batch = BatchJob(...)
    items = [BatchItem(...) for p in pairings]
    session.add_all([batch] + items)
    session.flush()  # Get IDs
    
    # 2. Prepare VtonJob records (do NOT publish to Celery yet)
    vton_jobs = [VtonJob(...) for item in items]
    session.add_all(vton_jobs)
    # Link batch_item_id
    for item, vton_job in zip(items, vton_jobs):
        item.vton_job_id = vton_job.id
    
    # 3. Commit — if this fails, no Celery tasks were sent
    await session.commit()

# 4. Publish Celery tasks AFTER successful commit
for vton_job in vton_jobs:
    await enqueue_vton_task.delay(vton_job.id)
```

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Outbox pattern** — write tasks to an `outbox` table, separate worker polls and publishes | Fully transactional, reliable, works with any message broker | Adds complexity: new table, polling worker, eventual consistency delay | Overkill for this use case; batch submission is synchronous API call, not event-driven |
| **Celery transactional integration** (e.g., `celery-once`, `django-celery`) | Seamless integration | Django-specific or requires additional packages; not compatible with FastAPI + SQLAlchemy async | Not applicable to current stack |
| **Idempotent VtonJob tasks with graceful degradation** — task checks if record exists, exits silently if not | Simple, no coordination needed | Wasted Celery worker cycles on orphaned tasks; error noise in logs; requires task-level idempotency | Acceptable as defense-in-depth, but doesn't prevent the root cause |
| **Publish after commit** (chosen) | Simple, no new infrastructure, guarantees no orphaned tasks | If Celery publish fails after DB commit, batch is created but items not enqueued (requires retry or manual intervention) | Best trade-off: simple, reliable for the common case, failure mode is detectable |

## Consequences

### Positive

- No orphaned Celery tasks — tasks are only published after DB records exist
- Simple implementation — no new tables, workers, or infrastructure
- Consistent with existing FastAPI patterns — `session.commit()` is already the transaction boundary
- Failure mode is clear: if Celery publish fails, the batch exists but items are not enqueued (can be retried)

### Negative

- If Celery publish fails after commit, the batch is in a partially-created state (records exist, no tasks queued)
- Requires manual retry or a reconciliation mechanism for the failure case
- The 500ms API response budget now includes Celery publish time (not just DB commit)

### Risks

- **Celery broker unavailable after commit**: Batch created but items not enqueued. Mitigation: return `pending` status and implement a retry endpoint or background reconciliation job. The batch can be retried via `POST /api/batches/{id}/retry` (future story).
- **Partial Celery publish failure** (some tasks sent, some fail): Batch items have inconsistent `vton_job_id` state. Mitigation: wrap Celery publishing in a loop with retry; if any fail, log and mark batch as `pending` for manual retry.

## Related

- **Stories**: 001-create-batch-job, 002-enqueue-batch-items
- **Standards**: Should be added to coding-standards.md under "Async task publishing"
- **Previous ADRs**: None

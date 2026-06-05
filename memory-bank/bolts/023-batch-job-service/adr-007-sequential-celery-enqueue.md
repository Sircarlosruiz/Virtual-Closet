---
bolt: 023-batch-job-service
created: 2026-06-04T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-007: Sequential Celery Task Publishing for Batch Enqueue

## Context

When a batch of up to 100 items is submitted, each item must be enqueued as an individual Celery `VtonJob` task. The API must respond within 500ms. Publishing 100 Celery tasks sequentially via `task.delay()` involves 100 network round-trips to RabbitMQ, which may exceed the time budget depending on broker latency.

We need a strategy that keeps the total enqueue time within the 500ms budget while maintaining simplicity and reliability.

## Decision

Use **sequential `task.delay()` publishing** after database commit, with the following optimizations:

1. **DB commit is the critical path** — all 100 `VtonJob` records are created in a single bulk INSERT within the transaction. This is fast (~50-100ms for 100 rows).
2. **Celery publishing happens after commit** — tasks are published sequentially via `task.delay()`. RabbitMQ is on the same Docker Compose network in dev, and on the same k3s node in prod, so latency is ~1-5ms per task. For 100 tasks: ~100-500ms worst case.
3. **API returns immediately after DB commit** — the response is sent to the client after the transaction commits, **before** Celery tasks are fully published. The batch status is `in-progress` and the client polls for status.

This means the 500ms budget applies to DB operations only, not Celery publishing. Celery publishing happens asynchronously after the response is sent (fire-and-forget with logging).

**Implementation**:
```python
@router.post("/api/batches")
async def create_batch(request: BatchCreateRequest, mayorista = Depends(get_current_mayorista)):
    async with session.begin():
        # 1. Validate, create BatchJob + BatchItem + VtonJob records
        batch = await batch_service.create(session, mayorista.id, request)
        await session.commit()
    
    # 2. Response sent to client — batch is "in-progress"
    # 3. Celery tasks published in background (fire-and-forget)
    background_tasks.add_task(enqueue_batch_items, batch.id)
    
    return BatchResponse.from_orm(batch)
```

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Celery `group()` primitive** — publish all tasks as a single group | Single broker round-trip, atomic group execution | Group results are complex to manage; individual task tracking is harder; not designed for fire-and-forget | Overkill — we need individual `VtonJob` tracking, not group semantics |
| **RabbitMQ batch publishing** — use `pika` directly with batch publish | Very fast, single network call | Bypasses Celery abstraction; requires direct RabbitMQ client; loses Celery retry/monitoring | Breaks existing architecture — Celery is the task abstraction layer |
| **Background task after response** (chosen) | API responds within 500ms (DB only); Celery publishing is async; simple implementation | If background task fails, batch items are not enqueued; requires monitoring | Best trade-off: meets NFR, simple, failure mode is detectable (batch stuck in `in-progress`) |
| **Synchronous sequential publish within request** | Simple, all-or-nothing within request | May exceed 500ms for large batches; client waits for full enqueue | Violates NFR for 100-item batches |

## Consequences

### Positive

- API responds within 500ms — only DB operations are in the critical path
- Simple implementation — uses FastAPI's `BackgroundTasks`
- Celery publishing failure doesn't affect the HTTP response
- Batch status polling reveals if items were enqueued (items with `vton_job_id = NULL` are not yet enqueued)

### Negative

- If background task fails, batch is created but items are not enqueued — batch stuck in `in-progress`
- Requires monitoring/alerting for batches stuck in `in-progress` without `vton_job_id`
- Client may poll and see items with `pending` status for a few seconds before they transition to `processing`

### Risks

- **Background task process crash**: If the FastAPI worker crashes before publishing all tasks, some items are enqueued and others are not. Mitigation: implement a reconciliation job that scans for `in-progress` batches with items missing `vton_job_id` and enqueues them. This is a future story (003-track-item-status covers this).
- **RabbitMQ unavailable**: Background task fails, items not enqueued. Mitigation: retry with exponential backoff in the background task; after max retries, log error and mark batch as `failed`.

## Related

- **Stories**: 001-create-batch-job, 002-enqueue-batch-items
- **Standards**: Should be added to coding-standards.md under "Background task patterns"
- **Previous ADRs**: ADR-004 (separate Celery queue for TryOff jobs) — batch jobs should use the existing `vton` queue

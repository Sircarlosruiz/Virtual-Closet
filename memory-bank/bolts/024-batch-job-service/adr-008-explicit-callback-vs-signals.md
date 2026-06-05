---
bolt: 024-batch-job-service
created: 2026-06-04T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-008: Explicit Callback in VtonJob Task for Batch Completion

## Context

When a `VtonJob` completes or fails, the corresponding `BatchItem` must be updated and batch counters adjusted. The existing `process_vton_job` Celery task handles VTON inference and updates the `VtonJob` record. We need to extend this flow to also handle batch-related updates when the job belongs to a batch (i.e., when `VtonJob.batch_item_id` is set).

Two approaches are available:
1. **Explicit callback**: Add a call to `BatchCompletionHandler` at the end of the existing `process_vton_job` task.
2. **Celery signals**: Use Celery's global `task_success` and `task_failure` signal handlers to intercept all task completions and check for batch context.

## Decision

Use **explicit callback** in the existing `process_vton_job` task. Add a conditional call after the VtonJob status update:

```python
# tasks/vton_task.py (existing task, minimal modification)
@shared_task(bind=True, max_retries=3)
def process_vton_job(self, vton_job_id: str):
    # ... existing inference logic ...
    
    if success:
        await repo.update_status(vton_job_id, "completed", result_minio_key=result_key)
        
        # Explicit batch callback (only if job belongs to a batch)
        if vton_job.batch_item_id:
            await batch_handler.on_vton_job_complete(vton_job_id, result_key)
    else:
        await repo.update_status(vton_job_id, "failed", error_reason=error)
        
        if vton_job.batch_item_id:
            await batch_handler.on_vton_job_failed(vton_job_id, error)
```

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Celery `task_success`/`task_failure` signals** | Zero modification to existing task; decoupled from VtonJob logic | Global signals fire for ALL tasks (not just VtonJob); harder to test; signal handlers run in separate context (no async DB session); error in signal doesn't trigger task retry | Signals are too implicit and global; async DB session management is complex in signal handlers; harder to trace execution flow |
| **Celery chord** — wrap VtonJob in a chord with batch callback as callback task | Clean separation; chord handles success/failure | Requires changing how VtonJob is submitted (from `delay()` to `chord()`); breaks existing single-item VTON flow; adds Celery complexity | Too invasive for existing flow; chords have known reliability issues with some result backends |
| **Event bus / pub-sub** — VtonJob publishes event, batch handler subscribes | Fully decoupled; extensible | Requires new infrastructure (event bus); over-engineering for a single subscriber | No existing event bus in the codebase; adds unnecessary complexity |
| **Explicit callback** (chosen) | Simple, traceable, testable; conditional on `batch_item_id` so single-item flow is unaffected; callback runs in same task context (same retry policy) | Requires modifying existing task file; tight coupling between VtonJob and batch domain | Best trade-off: minimal change, clear flow, easy to test, same retry semantics |

## Consequences

### Positive

- Clear execution flow — callback is visible in the task code
- Same retry policy applies to callback — if callback fails, task retries
- Conditional on `batch_item_id` — single-item VTON jobs are unaffected (backward compatible)
- Easy to unit test — mock the callback and verify it's called with correct arguments
- Error handling is explicit — can catch and log callback errors without affecting VtonJob status update

### Negative

- Modifies existing `process_vton_job` task — requires careful code review
- Tight coupling between VtonJob task and batch domain (mitigated by conditional check)
- If `BatchCompletionHandler` raises an unhandled exception, the VtonJob task fails and retries (may re-process inference)

### Risks

- **Callback failure causes task retry**: If the callback fails after VtonJob is marked complete, the task retries and may re-run inference. Mitigation: wrap callback in try/except; log errors but don't re-raise. VtonJob status is already committed, so retry is safe (idempotent inference check).
- **Migration order**: If callback code deploys before migration (adding `batch_item_id`), the conditional check `if vton_job.batch_item_id` handles it gracefully (NULL → no callback).

## Related

- **Stories**: 003-track-item-status, 004-partial-failure-isolation
- **Standards**: Should be noted in coding-standards.md under "Celery task extension patterns"
- **Previous ADRs**: ADR-004 (separate Celery queue), ADR-007 (sequential Celery enqueue)

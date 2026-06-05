---
unit: 001-batch-job-service
bolt: 024-batch-job-service
stage: design
status: complete
created: 2026-06-04T00:00:00Z
---

# Technical Design - Batch Job Service (Status, Isolation, Retry)

## Architecture Pattern

**Layered / Domain-Driven within FastAPI monolith** — Consistent with bolt 023. Adds Celery signal/callback layer for async event handling, keeping the callback logic separate from the HTTP request layer.

## Layer Structure

```text
┌──────────────────────────────────────────────────────────┐
│      Presentation (api/routers/batches.py)               │  POST /api/batches/{id}/items/{item_id}/retry
│      Pydantic schemas (api/schemas/batches.py)           │  Retry response schema
├──────────────────────────────────────────────────────────┤
│      Application (services/batch_retry_service.py)       │  BatchRetryService: validate, create VtonJob, reset item
├──────────────────────────────────────────────────────────┤
│      Domain (services/batch_completion_handler.py)       │  BatchCompletionHandler: on_vton_complete, on_vton_fail
│                                                         │  Status state machine, counter logic
├──────────────────────────────────────────────────────────┤
│     Infrastructure (repositories/batch_repo.py)          │  F() expression counter updates, callback lookups
│     Celery signals (tasks/batch_signals.py)             │  Celery task_success/task_failure signal handlers
└──────────────────────────────────────────────────────────┘
```

## API Design

### POST /api/batches/{batch_id}/items/{item_id}/retry
- **Method**: POST
- **Auth**: `Depends(get_current_mayorista)`
- **Path params**: `batch_id` (UUID), `item_id` (UUID)
- **Request Body**: None (empty POST)
- **Response** (200 OK):
```json
{
  "id": "uuid",
  "batch_id": "uuid",
  "status": "pending",
  "vton_job_id": "uuid",
  "retry_count": 1,
  "error_message": null
}
```
- **Errors**:
  - `404`: Batch or item not found
  - `403`: Batch doesn't belong to mayorista
  - `409`: Item is not in `failed` status (already complete or still processing)
  - `503`: Retry enqueue failed

## Data Persistence

### Schema Changes
No new tables. Existing `batch_jobs` and `batch_items` tables from bolt 023 support all operations.

### Counter Update Strategy (Atomic)
```python
# repositories/batch_repo.py
from sqlalchemy import update

async def increment_completed_count(self, batch_id: uuid.UUID) -> int:
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

Uses SQLAlchemy `UPDATE ... SET completed_count = completed_count + 1` which is atomic at the database level. No `SELECT` then `UPDATE` — prevents lost updates under concurrent access.

### Status Computation Logic
```python
def compute_batch_status(completed_count: int, failed_count: int, total_items: int) -> str:
    if completed_count + failed_count < total_items:
        return "in-progress"
    if completed_count == total_items:
        return "complete"
    if failed_count == total_items:
        return "failed"
    return "partial"  # mixed results
```

## Celery Callback Wiring

### Approach: Celery Signal Handlers
Use Celery's `task_success` and `task_failure` signals to intercept VtonJob completion. The signal handler:
1. Looks up the `VtonJob` by task result
2. Checks if `vton_job.batch_item_id` is set
3. If set, calls `BatchCompletionHandler.on_vton_job_complete()` or `on_vton_job_failed()`

```python
# tasks/batch_signals.py
from celery.signals import task_success, task_failure

@task_success.connect
def handle_vton_success(sender=None, result=None, **kwargs):
    # result contains the VtonJob ID or result_minio_key
    # Look up VtonJob, check batch_item_id, update BatchItem
    ...

@task_failure.connect
def handle_vton_failure(sender=None, exception=None, **kwargs):
    # Look up VtonJob, check batch_item_id, mark BatchItem failed
    ...
```

### Alternative: Explicit Callback in VtonJob Task
If signal-based approach is too implicit, add an explicit callback call at the end of the existing `process_vton_job` task:

```python
# tasks/vton_task.py (existing, modified minimally)
@shared_task
def process_vton_job(vton_job_id: str):
    # ... existing inference logic ...
    if success:
        # ... existing success handling ...
        await batch_completion_handler.on_vton_job_complete(vton_job_id, result_key)
    else:
        await batch_completion_handler.on_vton_job_failed(vton_job_id, error)
```

**Decision**: Use explicit callback (alternative 2) to avoid signal coupling and make the flow traceable. Signal handlers are global and harder to test.

## Security Design

| Concern | Approach |
|---------|----------|
| **Retry Authorization** | Verify `batch.mayorista_id == current_user.id` before allowing retry |
| **Item Ownership** | Item must belong to a batch owned by the requesting mayorista |
| **Idempotency** | Retry on non-failed item returns 409; retry on already-retried item (still failed) is allowed |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| **Concurrency Safety** | `F()` expressions for counter updates — no SELECT-then-UPDATE race conditions |
| **Isolation** | Each `BatchItem` has independent Celery task; failure of one doesn't affect siblings |
| **Retry Performance** | Single DB transaction: reset item + create VtonJob + update counters |
| **Callback Reliability** | Explicit callback in VtonJob task — if callback fails, task retries (Celery retry policy) |

## Error Handling

| Error Type | HTTP Status | Response |
|------------|-------------|----------|
| `ItemNotFailedError` | 409 | `{"detail": {"code": "ITEM_NOT_FAILED", "message": "Can only retry failed items", "context": {"current_status": "..."}}}` |
| `ItemNotFoundError` | 404 | `{"detail": {"code": "ITEM_NOT_FOUND", "message": "Batch item not found"}}` |
| `RetryEnqueueError` | 503 | `{"detail": {"code": "RETRY_FAILED", "message": "Failed to enqueue retry", "context": {"reason": "..."}}}` |

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| **VtonJobService** (existing) | Creates new VtonJob for retry | Python function call |
| **Celery / RabbitMQ** | Async task execution + callback | Explicit callback in existing task |
| **PostgreSQL** | Atomic counter updates | SQLAlchemy `UPDATE ... RETURNING` |

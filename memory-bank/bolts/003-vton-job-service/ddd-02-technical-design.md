---
unit: 002-vton-job-service
bolt: 003-vton-job-service
stage: design
status: complete
updated: 2026-05-27T00:10:00Z
---

# Technical Design - VTON Job Service (Retry + History Extension)

## Architecture Pattern

**Extension of existing layered architecture** — No new architectural patterns. This bolt extends the Celery task from bolt 002 with retry logic and adds a new paginated list endpoint to the existing VTON router.

## Layer Structure (Changes Only)

```text
┌─────────────────────────────────────┐
│      Presentation                   │  api/routers/vton.py (ADD: GET /api/vton/jobs)
│      api/schemas/vton.py            │  ADD: VTONJobHistoryResponse
├─────────────────────────────────────┤
│      Application                    │  services/vton_job_service.py (ADD: list_jobs)
│                                     │  services/retry_policy.py (NEW)
├─────────────────────────────────────┤
│        Domain                       │  (no changes — model from bolt 002 sufficient)
├─────────────────────────────────────┤
│     Infrastructure                  │  tasks/vton_task.py (UPDATE: retry logic)
│                                     │  core/config.py (ADD: retry env vars)
└─────────────────────────────────────┘
```

## API Design (New Endpoint)

### Endpoint

| Endpoint | Method | Request | Response | Auth |
|----------|--------|---------|----------|------|
| `/api/vton/jobs` | GET | Query: `page?`, `page_size?` | `200` → `{ items: [...], total, page, page_size }` | Required |

### New Pydantic Schema

```python
class VTONJobHistoryItem(BaseModel):
    job_id: UUID
    status: JobStatus
    cloth_type: ClothType
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_url: str | None = None
    error_reason: str | None = None
    retry_count: int = 0

class VTONJobHistoryResponse(BaseModel):
    items: list[VTONJobHistoryItem]
    total: int
    page: int
    page_size: int
```

## Celery Retry Strategy

### Approach: Manual Retry with Exponential Backoff

Rather than using Celery's `autoretry_for`, we implement **manual retry logic** to:
1. Track `retry_count` in PostgreSQL (not just in Celery state)
2. Update job status to `queued` between retries (so polls reflect the retry state)
3. Classify errors as retriable vs non-retriable
4. Apply exponential backoff with configurable base delay

### Updated Task Flow

```python
@app.task(bind=True, name="tasks.vton_task.process_vton_job", acks_late=True)
def process_vton_job(self, job_id: str) -> None:
    try:
        # ... existing steps 1-4 ...
        # Step 4: Call VTONProvider.generate()
        result_bytes = asyncio.run(provider.generate(...))
        # ... existing steps 5-6 (success path) ...

    except Exception as exc:
        # Classify error
        if is_retriable_error(exc):
            if job.retry_count < job.max_retries:
                # Schedule retry with exponential backoff
                delay = get_retry_delay(job.retry_count)
                job.retry_count += 1
                job.status = "queued"  # Reset to queued for retry
                job.error_reason = str(exc)
                session.commit()
                # Re-queue with countdown
                self.retry(exc=exc, countdown=delay)
            else:
                # Max retries exceeded → permanently failed
                job.status = "failed"
                job.error_reason = f"Failed after {job.max_retries} retries: {exc}"
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
        else:
            # Non-retriable error → fail immediately
            job.status = "failed"
            job.error_reason = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
```

### Error Classification

```python
def is_retriable_error(exc: Exception) -> bool:
    """Determine if an error should trigger a retry."""
    # Timeout errors → retriable
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return True

    # Connection errors → retriable
    if isinstance(exc, (ConnectionError, httpx.ConnectError)):
        return True

    # Replicate 429 (rate limit) → retriable with longer backoff
    if isinstance(exc, ReplicateError) and getattr(exc, "status", None) == 429:
        return True

    # Replicate 5xx → retriable
    if isinstance(exc, ReplicateError) and getattr(exc, "status", 0) >= 500:
        return True

    # Replicate 4xx (except 429) → NOT retriable
    if isinstance(exc, ReplicateError) and getattr(exc, "status", 0) >= 400:
        return False

    # Generic HTTP errors
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 429:
            return True
        if exc.response.status_code >= 500:
            return True
        return False  # 4xx (except 429) → not retriable

    # Default: retriable (safe fallback for unknown errors)
    return True
```

### Exponential Backoff Formula

```
delay = min(base_delay * (2 ** retry_count), max_delay)
```

| Retry # | Delay (base=30s, max=600s) |
|---------|---------------------------|
| 0 → 1 | 30s |
| 1 → 2 | 60s |
| 2 → 3 | 120s |
| 3 → 4 | 240s (if max_retries > 3) |

### Configuration (New Env Vars)

| Env Var | Default | Description |
|---------|---------|-------------|
| `VTON_MAX_RETRIES` | 3 | Maximum number of retry attempts |
| `VTON_RETRY_BASE_DELAY_SECONDS` | 30 | Base delay for exponential backoff |
| `VTON_RETRY_MAX_DELAY_SECONDS` | 600 | Maximum delay cap (10 minutes) |

## History Endpoint Design

### Service Layer

```python
async def list_jobs(
    self,
    mayorista_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """List mayorista's VTON jobs with pagination."""
    jobs, total = await self._vton_job_repo.list_by_mayorista(
        mayorista_id, page, page_size
    )
    results = []
    for job in jobs:
        item = {
            "job_id": job.id,
            "status": job.status,
            "cloth_type": job.cloth_type,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "result_url": None,
            "error_reason": job.error_reason,
            "retry_count": job.retry_count,
        }
        if job.status == "completed" and job.result_minio_key:
            item["result_url"] = await self._minio.get_presigned_url(
                bucket="generated", key=job.result_minio_key
            )
        results.append(item)
    return results, total
```

## Security Design (No Changes)

- History endpoint uses `Depends(get_current_mayorista)` — only returns jobs owned by the authenticated mayorista
- Repository query already filters by `mayorista_id` (created in bolt 002)

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| Retry delay | Exponential backoff with configurable base/max delay |
| History pagination | Page-based pagination (page + page_size) with max 100 per page |
| History response time | Indexed query on `(mayorista_id, created_at DESC)` — p95 < 200ms |
| No orphaned retries | `retry_count` tracked in DB; Celery `acks_late=True` ensures re-delivery on worker crash |

## Error Handling (Updated)

| Error Type | HTTP Code | Response |
|------------|-----------|----------|
| Not authenticated | 401 | `{"detail": "Not authenticated"}` |

## External Dependencies (No Changes)

| Service | Purpose | Integration |
|---------|---------|-------------|
| RabbitMQ | Task re-queue for retries | AMQP via Celery `self.retry(countdown=...)` |
| Celery Worker | Retry execution with backoff | `tasks/vton_task.py` |
| PostgreSQL | Retry count persistence | `vton_jobs.retry_count` column |
| MinIO | Result presigned URLs for history | `core/minio_client.py` |

## Files to Create/Modify

### New Files
1. `services/retry_policy.py` — `RetryPolicy` class with backoff calculation and error classification

### Modified Files
1. `tasks/vton_task.py` — Add retry logic, error classification, exponential backoff
2. `api/routers/vton.py` — Add `GET /api/vton/jobs` endpoint
3. `api/schemas/vton.py` — Add `VTONJobHistoryItem`, `VTONJobHistoryResponse`
4. `services/vton_job_service.py` — Add `list_jobs` method
5. `core/config.py` — Add `VTON_RETRY_BASE_DELAY_SECONDS`, `VTON_RETRY_MAX_DELAY_SECONDS`

### No New Migration
- `vton_jobs` table already has `retry_count`, `max_retries`, `error_reason` columns from bolt 002

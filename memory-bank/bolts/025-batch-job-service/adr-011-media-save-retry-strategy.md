---
bolt: 025-batch-job-service
created: 2026-06-04T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-011: Celery Retry with Error Flag for Media Save Failures

## Context

When a `BatchItem` completes, its result image must be saved to the media library (MinIO). MinIO may be temporarily unavailable (network partition, maintenance, overload). The media save happens in the Celery completion callback, which runs after the VtonJob status is already committed.

Two failure handling strategies are available:
1. **Retry with Celery retry policy**: If media save fails, retry with exponential backoff (up to 3 attempts). If all retries fail, flag the error for manual intervention.
2. **Fail silently**: Log the error, set `media_save_error` flag, and let the mayorista manually re-save the image.

## Decision

Use **Celery retry with error flag**: attempt media save with up to 3 retries (exponential backoff: 30s, 60s, 120s). If all retries fail, set `BatchItem.media_save_error = true` and log the final error. The mayorista can then manually re-save the image via a future "retry media save" endpoint.

```python
# services/batch_media_save_service.py
from celery import shared_task

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def save_batch_item_media(self, batch_id: str, item_id: str, result_minio_key: str):
    try:
        media_item = await media_service.save(
            minio_key=result_minio_key,
            metadata={...},
        )
        await batch_repo.set_result_media(uuid.UUID(item_id), media_item.id)
    except (MinIOError, ConnectionError) as exc:
        if self.request.retries < self.max_retries:
            self.retry(exc=exc, countdown=self.default_retry_delay * (2 ** self.request.retries))
        else:
            # All retries exhausted — flag for manual intervention
            await batch_repo.set_media_save_error(uuid.UUID(item_id), str(exc))
            logger.error(
                "Media save failed for item %s after %d retries: %s",
                item_id, self.max_retries, exc,
            )
```

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Retry only (no error flag)** | Automatic recovery; no manual intervention needed | If MinIO is down for hours, retries exhaust and error is lost; no visibility | No audit trail for permanently failed saves; mayorista has no way to know |
| **Fail silently (no retry)** | Simple; no Celery complexity | Transient failures (30s network blip) cause permanent data loss | Wasteful — many failures are transient and would succeed with retry |
| **Retry + error flag** (chosen) | Handles transient failures automatically; flags permanent failures for manual action | More complex; requires error flag column; manual intervention needed for permanent failures | Best trade-off: automatic recovery for common case, visibility for edge case |
| **Dead letter queue** | Failed saves are queued for later processing | Requires new infrastructure (DLQ table, reprocessing worker) | Overkill for media save — simpler to flag and let mayorista retry |

## Consequences

### Positive

- **Automatic recovery**: Transient MinIO failures (network blips, brief maintenance) are handled automatically
- **Visibility**: Permanent failures are flagged (`media_save_error = true`) for manual intervention
- **No data loss**: Failed saves are logged and auditable
- **Exponential backoff**: Prevents overwhelming MinIO during extended outages

### Negative

- Requires `media_save_error` column on `batch_items` table
- Requires a future "retry media save" endpoint for manual recovery
- Celery task adds complexity to the callback flow
- Mayorista may see incomplete media library until manual retry

### Risks

- **Retry storm**: If many items fail simultaneously, retries could overwhelm MinIO when it recovers. Mitigation: exponential backoff with jitter; consider rate limiting retry tasks.
- **Callback timeout**: If media save + retries takes too long, the Celery task may timeout. Mitigation: set appropriate `soft_time_limit` and `time_limit` on the task; retries are independent of the main VtonJob task.

## Related

- **Stories**: 006-auto-save-to-media-library
- **Standards**: Should be noted in coding-standards.md under "Celery retry patterns"
- **Previous ADRs**: ADR-008 (explicit callback), ADR-009 (atomic counter updates)

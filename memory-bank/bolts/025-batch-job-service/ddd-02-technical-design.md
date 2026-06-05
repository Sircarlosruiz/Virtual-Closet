---
unit: 001-batch-job-service
bolt: 025-batch-job-service
stage: design
status: complete
created: 2026-06-04T00:00:00Z
---

# Technical Design - Batch Job Service (Media Save, History)

## Architecture Pattern

**Layered / Domain-Driven within FastAPI monolith** — Consistent with bolts 023 and 024. Adds media save service layer and extends completion callback.

## Layer Structure

```text
┌──────────────────────────────────────────────────────────┐
│      Presentation (api/routers/batches.py)               │  GET /api/batches (list endpoint — already exists)
│      Pydantic schemas (api/schemas/batches.py)           │  BatchListResponse (already exists)
├──────────────────────────────────────────────────────────┤
│      Application (services/batch_media_save_service.py)  │  BatchMediaSaveService: save result to media library
├──────────────────────────────────────────────────────────┤
│      Domain (services/batch_completion_handler.py)       │  Extended: calls media save after status update
│                                                         │  Graceful degradation on media save failure
├──────────────────────────────────────────────────────────┤
│     Infrastructure (repositories/batch_repo.py)          │  set_result_media, set_media_save_error
│     Existing: services/media_library_service.py          │  Reuse existing media save logic
└──────────────────────────────────────────────────────────┘
```

## API Design

### GET /api/batches (List)
- **Already implemented** in bolt 023
- **Method**: GET
- **Auth**: `Depends(get_current_mayorista)`
- **Query params**: `page` (default 1), `page_size` (default 20, max 100)
- **Response** (200 OK):
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Colección Verano 2026",
      "status": "complete",
      "total_items": 20,
      "completed_count": 18,
      "failed_count": 2,
      "created_at": "2026-06-04T00:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```
- **Errors**: None (returns empty list for 0 batches)

## Media Save Flow

### Placement in Completion Callback
The media save is triggered **after** the BatchItem status is updated and counters are incremented:

```python
# services/batch_completion_handler.py (extended)
async def on_vton_job_complete(self, vton_job_id, result_minio_key):
    # 1. Update BatchItem status → complete
    # 2. Increment BatchJob.completed_count
    # 3. Compute and update BatchJob status
    # 4. Save to media library (NEW)
    try:
        await media_save_service.save_result(
            batch_id=item.batch_id,
            item_id=item.id,
            result_minio_key=result_minio_key,
        )
    except Exception:
        logger.warning("Media save failed for item %s", item.id)
        # Graceful degradation: don't fail the callback
```

### Idempotency Strategy
Before saving, check if `BatchItem.result_media_id` is already set:

```python
async def save_result(self, batch_id, item_id, result_minio_key):
    # Check idempotency
    if item.result_media_id is not None:
        return  # Already saved (duplicate callback)
    
    # Save to media library
    media_item = await media_service.save(
        minio_key=result_minio_key,
        metadata={
            "batch_id": str(batch_id),
            "batch_name": batch.name,
            "garment_id": str(item.garment_id),
            "model_id": str(item.model_id),
            "vton_job_id": str(vton_job_id),
        },
    )
    
    # Update item
    await batch_repo.set_result_media(item_id, media_item.id)
```

### Graceful Degradation
If media save fails (MinIO error, network issue):
1. Log the error
2. Set `BatchItem.media_save_error = true`
3. Do NOT change `BatchItem.status` (remains `complete`)
4. Do NOT increment/decrement batch counters
5. Do NOT raise exception (callback completes successfully)

## Data Persistence

### Schema Changes
No new tables. Existing `batch_items` table needs `media_save_error` column (boolean, default false, nullable):

```sql
ALTER TABLE batch_items ADD COLUMN media_save_error BOOLEAN DEFAULT FALSE;
```

### History Query
Already implemented in bolt 023:
```python
async def list_by_mayorista(self, mayorista_id, page, page_size):
    # Count
    count_stmt = select(func.count(BatchJob.id)).where(
        BatchJob.mayorista_id == mayorista_id
    )
    # List (reverse-chronological)
    list_stmt = (
        select(BatchJob)
        .where(BatchJob.mayorista_id == mayorista_id)
        .order_by(BatchJob.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
```

## Security Design

| Concern | Approach |
|---------|----------|
| **History Isolation** | All queries scoped to `mayorista_id` — no cross-mayorista data leakage |
| **Media Ownership** | Media items saved with `mayorista_id` from batch — only owner can access |
| **Pagination Limits** | `page_size` capped at 100 — prevents unbounded queries |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| **Media save within 5s** | Media save is async in Celery callback — doesn't block API response |
| **Idempotency** | Check `result_media_id` before save; prevents duplicates on duplicate callbacks |
| **Graceful degradation** | Media save failure doesn't affect batch status or counters |
| **History performance** | Indexed on `mayorista_id + created_at DESC`; pagination limits result set |

## Error Handling

| Error Type | Handling | Response |
|------------|----------|----------|
| MinIO unavailable | Log warning, set `media_save_error`, continue | No HTTP error (callback is async) |
| Media save timeout | Same as above | No HTTP error |
| Duplicate callback | Idempotency check skips save | No error |

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| **MediaLibraryService** (existing) | Save result image to media library | Python function call |
| **MinIO** | Object storage for media items | Via MediaLibraryService |
| **PostgreSQL** | Store `result_media_id` and `media_save_error` | SQLAlchemy async |

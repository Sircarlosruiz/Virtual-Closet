---
unit: 002-tryoff-job-service
bolt: 017-tryoff-job-service
stage: design
status: complete
updated: 2026-05-31T19:30:00Z
---

# Technical Design - 017-tryoff-job-service

## Architecture Pattern

**Layered Architecture** - Same pattern as bolt 016, extending existing TryOff service layer with media library integration and retry logic.

```text
┌─────────────────────────────────────────────────┐
│  Presentation (FastAPI)                         │
│  GET /api/tryoff/jobs/{job_id}                  │
├─────────────────────────────────────────────────┤
│  Application (TryoffJobService)                 │
│  get_job_status() with signed URL generation    │
├─────────────────────────────────────────────────┤
│  Domain (RetryPolicy, MediaLibraryService)      │
│  Retry decisions, media library integration     │
├─────────────────────────────────────────────────┤
│  Infrastructure (Celery, MinIO, httpx)          │
│  Retry logic, MinIO upload, signed URLs         │
└─────────────────────────────────────────────────┘
```

**Rationale**: Consistent with bolt 016. Extends existing service layer rather than creating new patterns. Media library integration is a natural extension of the job completion flow.

## Layer Structure

### Presentation Layer
- **Router**: `api/routers/tryoff.py` (existing, extended)
  - `GET /api/tryoff/jobs/{job_id}` - Enhanced to include signed output URL
  - No new endpoints (status polling already exists from bolt 016)

### Service Layer
- **TryoffJobService** (extended):
  - `get_job_status(job_id, mayorista_id)` - Now generates signed URL when job is complete
  - `save_extracted_garment(job_id)` - New method for media library integration
- **MediaLibraryService** (new):
  - `save_extracted_garment(mayorista_id, job_id, source_image_id, garment_type, image_bytes)` - Creates MediaItem with metadata
  - `generate_signed_url(minio_key, ttl_seconds=3600)` - Generates presigned URL for output image

### Domain Layer
- **RetryPolicy** (new):
  - `should_retry(retry_count, max_retries)` - Determines if retry is allowed
  - `get_delay(retry_count)` - Calculates exponential backoff delay (30s, 60s)
- **RetriableError / NonRetriableError** (new):
  - Exception types for retry decision logic

### Infrastructure Layer
- **Celery Task** (extended):
  - `process_tryoff_job` - Enhanced with retry logic and media library integration
  - Uses `self.retry()` for automatic retry with countdown
- **MinIO Client** (existing):
  - `upload_file(bucket, key, data, content_type)` - Idempotent upload
  - `get_presigned_url(bucket, key, expires=3600)` - Signed URL generation

## API Design

### GET /api/tryoff/jobs/{job_id}

**Enhanced Response Schema:**

```json
{
  "job_id": "uuid",
  "status": "pending|processing|complete|failed",
  "garment_type": "upper|lower|dress",
  "created_at": "2026-05-31T19:00:00Z",
  "started_at": "2026-05-31T19:00:05Z",
  "completed_at": "2026-05-31T19:01:30Z",
  "output_url": "https://minio.example.com/media/...?X-Amz-Signature=...",
  "error_message": null,
  "retry_count": 0
}
```

**Behavior by Status:**

| Status | output_url | error_message | Notes |
|--------|------------|---------------|-------|
| pending | null | null | Job queued, not yet picked up |
| processing | null | null | Worker processing (including retries) |
| complete | signed URL (1hr TTL) | null | Garment ready for use |
| failed | null | human-readable error | All retries exhausted |

**Error Responses:**
- 404: Job not found or not owned by mayorista (returns 404 to avoid enumeration)
- 422: Invalid job_id format (malformed UUID)

## Data Persistence

### TryoffJob Table (Extended)

**New columns added via Alembic migration:**

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| retry_count | Integer | 0 | Number of retry attempts |
| max_retries | Integer | 2 | Maximum allowed retries |
| last_error | Text | NULL | Last error message (truncated to 500 chars) |
| last_error_at | DateTime | NULL | Timestamp of last error |

**Migration:** `alembic/versions/{new}_add_retry_fields_to_tryoff_jobs.py`

### MediaItem Table (No Changes)

**Metadata JSON Schema for Extracted Garments:**

```json
{
  "type": "extracted_garment",
  "garment_type": "upper",
  "source_job_id": "uuid",
  "source_image_id": "uuid"
}
```

**Index for Querying Extracted Garments:**
```sql
CREATE INDEX idx_media_items_extracted_garments 
ON media_items ((metadata->>'type')) 
WHERE metadata->>'type' = 'extracted_garment';
```

## Security Design

### Authentication
- All endpoints require `get_current_mayorista` dependency (existing)
- No changes to auth flow

### Authorization
- Job status endpoint validates ownership via `get_by_id_and_mayorista`
- Returns 404 (not 403) if job doesn't belong to mayorista (prevents enumeration)
- MediaItem creation scoped to authenticated mayorista_id

### Data Protection
- Signed URLs expire after 1 hour (configurable)
- MinIO bucket access restricted to authenticated service account
- No PII in error messages (only technical error details)

## NFR Implementation

### Performance
- **Signed URL generation**: O(1) operation, < 10ms
- **Media library query**: Indexed on `metadata->>'type'` for fast filtering
- **Status polling**: Simple DB query, < 50ms response time

### Reliability
- **Idempotent MinIO uploads**: Deterministic key `{job_id}.png` ensures safe retries
- **Celery retry**: Automatic retry with exponential backoff (30s, 60s)
- **Max retries**: 2 retries (3 total attempts) before marking as failed
- **Error classification**: Retriable vs non-retriable errors prevent unnecessary retries

### Scalability
- **Media library**: Reuses existing MediaItem model, no new tables
- **MinIO**: Object storage scales horizontally
- **Celery**: Separate queue (`tryoff`) prevents resource contention

## Error Handling

### Retriable Errors (Trigger Retry)
| Error Type | Condition | Retry Behavior |
|------------|-----------|----------------|
| httpx.TimeoutException | Model service timeout | Retry with backoff |
| httpx.HTTPStatusError (5xx) | Model service internal error | Retry with backoff |
| MinIO ConnectionError | Storage service unavailable | Retry with backoff |
| Database ConnectionError | DB temporarily unavailable | Retry with backoff |

### Non-Retriable Errors (Fail Immediately)
| Error Type | Condition | Behavior |
|------------|-----------|----------|
| httpx.HTTPStatusError (4xx) | Client error (bad request) | Fail immediately |
| ValidationError | Invalid input data | Fail immediately |
| IntegrityError | DB constraint violation | Fail immediately |

### Error Response Format
```json
{
  "job_id": "uuid",
  "status": "failed",
  "error_message": "Model service timeout after 2 retries",
  "retry_count": 2
}
```

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| MinIO | Store extracted garment PNGs | S3 API (aiobotocore) |
| Celery | Async task execution with retry | AMQP (RabbitMQ) |
| FLUX Model Service | Garment extraction inference | HTTP/REST (httpx) |

## Celery Task Flow (Enhanced)

```python
@app.task(
    bind=True,
    name="tasks.tryoff_task.process_tryoff_job",
    acks_late=True,
    queue="tryoff",
    max_retries=2,
    default_retry_delay=30,
)
def process_tryoff_job(self, job_id: str) -> None:
    """Process TryOff job with retry and media library integration."""
    
    # 1. Load job from DB
    job = load_job(job_id)
    
    # 2. Idempotency check
    if job.status == "complete":
        return  # Already processed
    
    # 3. Update status to processing
    job.status = "processing"
    job.started_at = datetime.utcnow()
    save_job(job)
    
    try:
        # 4. Fetch source image from MinIO
        source_image = fetch_source_image(job.source_image_id)
        
        # 5. Call FLUX model service
        output_bytes = call_model_service(source_image, job.garment_type)
        
        # 6. Upload to MinIO (idempotent)
        minio_key = f"media/{job.mayorista_id}/extracted/{job_id}.png"
        upload_to_minio("generated", minio_key, output_bytes, "image/png")
        
        # 7. Create MediaItem in media library
        media_item = create_media_item(
            mayorista_id=job.mayorista_id,
            minio_key=minio_key,
            metadata={
                "type": "extracted_garment",
                "garment_type": job.garment_type,
                "source_job_id": str(job.id),
                "source_image_id": str(job.source_image_id),
            }
        )
        
        # 8. Mark job complete
        job.status = "complete"
        job.output_media_id = media_item.id
        job.completed_at = datetime.utcnow()
        save_job(job)
        
    except RetriableError as exc:
        # Retry with exponential backoff
        delay = 30 * (self.request.retries + 1)  # 30s, 60s
        job.retry_count += 1
        job.last_error = str(exc)[:500]
        job.last_error_at = datetime.utcnow()
        save_job(job)
        self.retry(exc=exc, countdown=delay)
        
    except NonRetriableError as exc:
        # Fail immediately
        job.status = "failed"
        job.last_error = str(exc)[:500]
        job.last_error_at = datetime.utcnow()
        job.completed_at = datetime.utcnow()
        save_job(job)
        
    except Exception as exc:
        # Default: retry if retries remain, else fail
        if self.request.retries < self.max_retries:
            self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
        else:
            job.status = "failed"
            job.last_error = str(exc)[:500]
            job.last_error_at = datetime.utcnow()
            job.completed_at = datetime.utcnow()
            save_job(job)
```

## Idempotency Design

### MinIO Upload
- **Key**: `media/{mayorista_id}/extracted/{job_id}.png`
- **Behavior**: Overwrites existing object with same key
- **Safe for retries**: Same job always produces same output key

### MediaItem Creation
- **Unique constraint**: `(mayorista_id, metadata->>'source_job_id')`
- **Behavior**: Upsert - if MediaItem exists for job_id, return existing
- **Safe for retries**: Duplicate attempts return existing MediaItem

### Job Status Updates
- **Idempotency guard**: Check job status before processing
- **Behavior**: Skip if job already complete
- **Safe for retries**: Celery acks_late ensures re-delivery on failure

## Migration Strategy

### Step 1: Add retry columns to tryoff_jobs
```python
def upgrade():
    op.add_column('tryoff_jobs', sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'))
    op.add_column('tryoff_jobs', sa.Column('max_retries', sa.Integer, nullable=False, server_default='2'))
    op.add_column('tryoff_jobs', sa.Column('last_error', sa.Text, nullable=True))
    op.add_column('tryoff_jobs', sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True))
```

### Step 2: Create index for media library queries
```python
def upgrade():
    op.create_index(
        'idx_media_items_extracted_garments',
        'media_items',
        [sa.text("(metadata->>'type')")],
        postgresql_where=sa.text("metadata->>'type' = 'extracted_garment'")
    )
```

### Step 3: Deploy and verify
- Run migration
- Verify existing jobs have retry_count=0, max_retries=2
- Test retry logic with simulated failures
- Verify media library integration

## Testing Strategy

### Unit Tests
- **RetryPolicy**: Test delay calculation, should_retry logic
- **MediaLibraryService**: Test metadata creation, idempotent upsert
- **TryoffJobService.get_job_status**: Test signed URL generation for complete jobs

### Integration Tests
- **Celery task retry**: Simulate 503 from model service, verify retry with backoff
- **Media library save**: Verify MediaItem created with correct metadata
- **Idempotency**: Run task twice with same job_id, verify single MediaItem

### Error Classification Tests
- **Retriable errors**: 503, timeout, connection error → retry
- **Non-retriable errors**: 400, 404, validation error → fail immediately

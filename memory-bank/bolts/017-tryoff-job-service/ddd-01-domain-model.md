---
stage: domain-model
bolt: 017-tryoff-job-service
status: complete
created: 2026-05-31T19:00:00Z
---

# Domain Model: 017-tryoff-job-service

## Context

Bolt 017 extends the TryOff job service with output handling, media library integration, and reliability features. This bolt builds on the foundation established in bolt 016 (job submission and Celery processing).

## Stories in Scope

- **004-poll-job-status**: GET /api/tryoff/jobs/{job_id} with signed output URL
- **005-media-library-save**: Auto-save extracted garments to media library
- **006-retry-on-failure**: Celery auto-retry with exponential backoff

## Entities

### TryoffJob (Extended)

**Existing entity from bolt 016, extended with retry tracking:**

```python
class TryoffJob(Base):
    # ... existing fields from bolt 016 ...
    
    # Retry tracking (story 006)
    retry_count: int = 0
    max_retries: int = 2
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
```

**Retry State Transitions:**
- `pending` → `processing` (first attempt)
- `processing` → `processing` (retry attempt, retry_count incremented)
- `processing` → `complete` (success on any attempt)
- `processing` → `failed` (all retries exhausted)

**Invariants:**
- `retry_count` never exceeds `max_retries`
- `last_error` is set when `status = failed`
- `output_media_id` is set when `status = complete`

### MediaItem (Reused)

**Existing entity from intent 001 (media-service), no schema changes:**

```python
class MediaItem(Base):
    id: UUID
    mayorista_id: UUID
    minio_key: str
    filename: str
    content_type: str
    metadata: JSON  # Flexible metadata field
    created_at: datetime
```

**Metadata Schema for Extracted Garments:**

```json
{
  "type": "extracted_garment",
  "garment_type": "upper|lower|dress",
  "source_job_id": "<tryoff_job_id>",
  "source_image_id": "<source_image_id>"
}
```

**Constraints:**
- `metadata->>'type' = 'extracted_garment'` identifies TryOff outputs
- `metadata->>'source_job_id'` links back to originating job (for idempotency)
- Unique constraint on `(mayorista_id, metadata->>'source_job_id')` prevents duplicates

## Value Objects

### SignedUrl

```python
@dataclass(frozen=True)
class SignedUrl:
    url: str
    expires_at: datetime
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
```

**TTL:** 1 hour (3600 seconds)

### RetryPolicy

```python
@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 2
    base_delay_seconds: int = 30
    
    def get_delay(self, retry_count: int) -> int:
        """Exponential backoff: 30s, 60s"""
        return self.base_delay_seconds * (retry_count + 1)
    
    def should_retry(self, retry_count: int) -> bool:
        return retry_count < self.max_retries
```

### RetriableError

```python
class RetriableError(Exception):
    """Errors that should trigger retry"""
    pass

class NonRetriableError(Exception):
    """Errors that should fail immediately"""
    pass
```

**Retriable Errors:**
- `httpx.TimeoutException`
- `httpx.HTTPStatusError` with 5xx status
- MinIO connection errors

**Non-Retriable Errors:**
- `httpx.HTTPStatusError` with 4xx status (client error)
- Validation errors
- Database constraint violations

## Aggregates

### TryoffJob Aggregate Root

**Boundary:** TryoffJob + associated MediaItem (created on completion)

**Invariants:**
1. MediaItem is created atomically with job completion
2. MinIO upload uses idempotent key: `media/{mayorista_id}/extracted/{job_id}.png`
3. Retry count is incremented before each retry attempt
4. Job status transitions are atomic (no intermediate states visible)

**Lifecycle:**
```
[Job Created] → pending
    ↓
[Worker Picks Up] → processing (retry_count = 0)
    ↓
[Model Call Fails - Retriable] → processing (retry_count = 1, retry in 30s)
    ↓
[Retry Succeeds] → complete (MediaItem created)
    OR
[Retry Fails - Retriable] → processing (retry_count = 2, retry in 60s)
    ↓
[Final Retry Succeeds] → complete (MediaItem created)
    OR
[Final Retry Fails] → failed (last_error set)
```

## Domain Services

### MediaLibraryService

```python
class MediaLibraryService:
    """Manages media library integration for extracted garments"""
    
    async def save_extracted_garment(
        self,
        mayorista_id: UUID,
        job_id: UUID,
        source_image_id: UUID,
        garment_type: str,
        image_bytes: bytes
    ) -> MediaItem:
        """
        Save extracted garment to media library.
        
        Idempotent: if MediaItem already exists for this job_id, return existing.
        MinIO upload uses deterministic key, so re-uploads overwrite safely.
        """
        pass
    
    async def get_signed_url(
        self,
        media_item: MediaItem,
        ttl_seconds: int = 3600
    ) -> SignedUrl:
        """Generate signed URL for media item"""
        pass
```

### RetryService

```python
class RetryService:
    """Manages retry logic for failed jobs"""
    
    def should_retry(self, job: TryoffJob, error: Exception) -> bool:
        """Determine if job should be retried"""
        if isinstance(error, NonRetriableError):
            return False
        if isinstance(error, RetriableError):
            return RetryPolicy().should_retry(job.retry_count)
        return False
    
    def get_retry_delay(self, job: TryoffJob) -> int:
        """Get delay in seconds before next retry"""
        return RetryPolicy().get_delay(job.retry_count)
    
    def record_failure(self, job: TryoffJob, error: Exception) -> None:
        """Record failure details for retry tracking"""
        job.retry_count += 1
        job.last_error = str(error)
        job.last_error_at = datetime.utcnow()
```

## Domain Events

### JobCompleted

```python
@dataclass
class JobCompleted:
    job_id: UUID
    mayorista_id: UUID
    output_media_id: UUID
    garment_type: str
    completed_at: datetime
```

**Triggered:** When job status transitions to `complete`

**Handlers:**
- Log completion metrics
- (Future) Notify UI via WebSocket

### JobFailed

```python
@dataclass
class JobFailed:
    job_id: UUID
    mayorista_id: UUID
    error_message: str
    retry_count: int
    failed_at: datetime
```

**Triggered:** When job status transitions to `failed` (all retries exhausted)

**Handlers:**
- Log failure metrics
- (Future) Alert operations team

## Repository Interfaces

### MediaItemRepository (Extended)

```python
class MediaItemRepository:
    async def create(self, item: MediaItem) -> MediaItem:
        pass
    
    async def find_by_job_id(
        self,
        mayorista_id: UUID,
        job_id: UUID
    ) -> Optional[MediaItem]:
        """Find MediaItem by source_job_id in metadata"""
        pass
    
    async def generate_signed_url(
        self,
        minio_key: str,
        ttl_seconds: int
    ) -> str:
        """Generate signed URL for MinIO object"""
        pass
```

### TryoffJobRepository (Extended)

```python
class TryoffJobRepository:
    # ... existing methods from bolt 016 ...
    
    async def increment_retry_count(
        self,
        job_id: UUID,
        error: str
    ) -> TryoffJob:
        """Increment retry count and record error"""
        pass
    
    async def mark_complete(
        self,
        job_id: UUID,
        output_media_id: UUID
    ) -> TryoffJob:
        """Mark job as complete with output"""
        pass
    
    async def mark_failed(
        self,
        job_id: UUID,
        error: str
    ) -> TryoffJob:
        """Mark job as failed (all retries exhausted)"""
        pass
```

## Integration Points

### MinIO Storage

**Path Convention:**
```
media/{mayorista_id}/extracted/{job_id}.png
```

**Idempotency:**
- Deterministic key based on job_id
- Re-uploads overwrite existing object
- No versioning needed (same job always produces same output)

### Celery Task (Extended)

```python
@app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue='tryoff'
)
def process_tryoff_job(self, job_id: str):
    """
    Process TryOff job with retry logic.
    
    Retry behavior:
    - Retriable errors: retry with exponential backoff
    - Non-retriable errors: fail immediately
    - Max 2 retries (3 total attempts)
    """
    pass
```

## Key Design Decisions

1. **Idempotent MinIO uploads**: Use deterministic key `{job_id}.png` so retries safely overwrite
2. **MediaItem metadata**: Use JSON field for flexibility, no schema changes needed
3. **Retry tracking in TryoffJob**: Keep retry state in job entity for observability
4. **Signed URL TTL**: 1 hour balances security and usability
5. **No distinct retry status**: Job shows `processing` during retry (simpler UI)

## Bounded Context

This bolt operates within the **TryOff Job Service** bounded context, extending the job processing pipeline with:
- Output persistence (MinIO + MediaItem)
- Reliability (retry logic)
- Observability (signed URLs for status polling)

Integration with external contexts:
- **Media Library** (intent 001): Reuses MediaItem entity
- **MinIO Storage** (infrastructure): Object storage for garment images
- **Celery** (infrastructure): Async task execution with retry

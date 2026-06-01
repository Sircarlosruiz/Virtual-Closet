---
unit: 002-tryoff-job-service
bolt: 016-tryoff-job-service
stage: design
status: complete
updated: 2026-05-31T16:00:00Z
---

# Technical Design - tryoff-job-service

## Architecture Pattern

**Layered Architecture** - Following the existing backend pattern (FastAPI + SQLAlchemy + Celery).

```
HTTP Client
    → api/routers/tryoff.py      (endpoints, auth, validation)
    → services/tryoff_job_service.py  (business logic, orchestration)
    → repositories/tryoff_job_repo.py (data access)
    → models/tryoff_job.py       (TryoffJob entity)
    
Celery Worker
    → tasks/tryoff_task.py       (async job processing)
    → services/tryoff_model_client.py (FLUX container HTTP client)
    → services/storage_service.py     (MinIO upload)
    → services/media_service.py       (media library integration)
```

## Layer Structure

### API Layer
- **Router**: `api/routers/tryoff.py`
  - `POST /api/tryoff/jobs` - single job submission
  - `POST /api/tryoff/jobs/batch` - multi-garment batch
- **Schemas**: `api/schemas/tryoff.py`
  - `TryoffJobRequest` - validates source_image_id and garment_type
  - `TryoffBatchRequest` - validates source_image_id and garment_types[]
  - `TryoffJobResponse` - returns job_id, status, garment_type
  - `TryoffBatchResponse` - returns list of jobs

### Service Layer
- **TryoffJobService**: `services/tryoff_job_service.py`
  - `create_job(mayorista_id, source_image_id, garment_type) → TryoffJob`
  - `create_batch(mayorista_id, source_image_id, garment_types[]) → TryoffJob[]`
  - Validates source image ownership via MediaService
  - Creates job records and enqueues Celery tasks
- **TryoffModelClient**: `services/tryoff_model_client.py`
  - `extract_garment(source_image_url, garment_type) → bytes`
  - httpx async client calling TRYOFF_MODEL_URL/tryoff
  - Timeout: 120s, retry on 503

### Repository Layer
- **TryoffJobRepo**: `repositories/tryoff_job_repo.py`
  - `save(job) → TryoffJob`
  - `find_by_id(job_id) → TryoffJob?`
  - `update_status(job_id, status, output_media_id?, error?) → TryoffJob`

### Model Layer
- **TryoffJob**: `models/tryoff_job.py`
  - SQLAlchemy model with status enum, timestamps, foreign keys
  - Indexes on mayorista_id and created_at

### Task Layer
- **process_tryoff_job**: `tasks/tryoff_task.py`
  - Celery task bound to `tryoff` queue
  - Reads job from DB, fetches source image from MinIO
  - Calls model service, uploads output to MinIO
  - Creates media library entry, updates job status

## API Design

### POST /api/tryoff/jobs

**Request**:
```json
{
  "source_image_id": "uuid",
  "garment_type": "upper" | "lower" | "dress"
}
```

**Response** (201 Created):
```json
{
  "job_id": "uuid",
  "status": "pending",
  "garment_type": "upper",
  "created_at": "2026-05-31T15:00:00Z"
}
```

**Errors**:
- 400: Invalid source_image_id format
- 404: Source image not found or not owned by mayorista
- 422: Invalid garment_type

### POST /api/tryoff/jobs/batch

**Request**:
```json
{
  "source_image_id": "uuid",
  "garment_types": ["upper", "lower"]
}
```

**Response** (201 Created):
```json
{
  "jobs": [
    {
      "job_id": "uuid",
      "status": "pending",
      "garment_type": "upper",
      "created_at": "2026-05-31T15:00:00Z"
    },
    {
      "job_id": "uuid",
      "status": "pending",
      "garment_type": "lower",
      "created_at": "2026-05-31T15:00:00Z"
    }
  ]
}
```

**Errors**:
- 400: Invalid source_image_id format
- 404: Source image not found or not owned by mayorista
- 422: Empty garment_types array or invalid types
- 422: Duplicate garment_types (de-duplicated automatically)

## Data Model

### tryoff_jobs Table

```sql
CREATE TABLE tryoff_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mayorista_id UUID NOT NULL REFERENCES mayorista(id) ON DELETE CASCADE,
    source_image_id UUID NOT NULL REFERENCES media_items(id) ON DELETE RESTRICT,
    garment_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    output_media_id UUID REFERENCES media_items(id) ON DELETE SET NULL,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT ck_tryoff_jobs_garment_type 
        CHECK (garment_type IN ('upper', 'lower', 'dress')),
    CONSTRAINT ck_tryoff_jobs_status 
        CHECK (status IN ('pending', 'processing', 'complete', 'failed'))
);

CREATE INDEX idx_tryoff_jobs_mayorista ON tryoff_jobs(mayorista_id);
CREATE INDEX idx_tryoff_jobs_mayorista_created ON tryoff_jobs(mayorista_id, created_at DESC);
CREATE INDEX idx_tryoff_jobs_source_image ON tryoff_jobs(source_image_id);
```

## Security Design

### Authentication
- **Endpoint Protection**: All endpoints require `get_current_mayorista` dependency
- **Ownership Validation**: Service layer validates source_image_id belongs to authenticated mayorista
- **No Public Access**: All endpoints are authenticated

### Authorization
- **Mayorista Isolation**: Jobs are scoped to mayorista_id
- **Cross-tenant Prevention**: Repository queries always filter by mayorista_id

## NFR Implementation

### Performance
- **Async Processing**: Celery tasks run in separate workers
- **Separate Queue**: `tryoff` queue prevents starvation of VTON jobs
- **Connection Pooling**: Reuse existing SQLAlchemy async session pool
- **HTTP Client Pooling**: httpx.AsyncClient with connection pooling for model service calls

### Reliability
- **Job Persistence**: Jobs created in DB before enqueuing (no lost jobs)
- **Idempotency**: Celery task checks job status before processing (skip if already complete)
- **Timeouts**: 120s timeout on model service calls
- **Error Handling**: Model service errors captured in job.error field

### Scalability
- **Horizontal Scaling**: Celery workers can scale independently
- **Queue Isolation**: Separate queue allows independent scaling of tryoff vs VTON processing

## Integration Points

### Model Service Client
```python
class TryoffModelClient:
    def __init__(self):
        self.base_url = settings.TRYOFF_MODEL_URL  # http://tryoff-model:8000
        self.timeout = 120.0
    
    async def extract_garment(
        self, 
        source_image_url: str, 
        garment_type: str
    ) -> bytes:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/tryoff",
                data={"garment_type": garment_type},
                files={"image": ("source.jpg", await self._fetch_image(source_image_url))}
            )
            response.raise_for_status()
            return response.content
```

### Celery Task Flow
```python
@celery_app.task(bind=True, queue="tryoff")
def process_tryoff_job(self, job_id: str):
    # 1. Load job from DB
    # 2. Check if already complete (idempotency)
    # 3. Update status to processing
    # 4. Fetch source image from MinIO
    # 5. Call model service
    # 6. Upload output to MinIO
    # 7. Create media library entry
    # 8. Update job status to complete with output_media_id
    # 9. On error: update status to failed, capture error message
```

## File Structure

```
backend/
├── models/
│   └── tryoff_job.py              # TryoffJob SQLAlchemy model
├── repositories/
│   └── tryoff_job_repo.py         # TryoffJobRepo CRUD operations
├── services/
│   ├── tryoff_job_service.py      # TryoffJobService business logic
│   └── tryoff_model_client.py     # TryoffModelClient HTTP client
├── tasks/
│   └── tryoff_task.py             # process_tryoff_job Celery task
├── api/
│   ├── schemas/
│   │   └── tryoff.py              # Pydantic request/response models
│   └── routers/
│       └── tryoff.py              # FastAPI endpoints
└── alembic/
    └── versions/
        └── {timestamp}_add_tryoff_jobs.py  # Migration script
```

## Environment Variables

- `TRYOFF_MODEL_URL`: URL of FLUX model service (default: `http://tryoff-model:8000`)
- `TRYOFF_QUEUE_NAME`: Celery queue name (default: `tryoff`)

## Migration Strategy

1. Create `tryoff_jobs` table with all columns and indexes
2. No data migration needed (new feature)
3. Register router in `main.py`
4. Register Celery task in `tasks/__init__.py`

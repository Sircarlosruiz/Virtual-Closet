---
unit: 002-vton-job-service
bolt: 002-vton-job-service
stage: design
status: complete
updated: 2026-05-26T23:40:00Z
---

# Technical Design - VTON Job Service

## Architecture Pattern

**Layered / Domain-Driven within monolith** — Consistent with existing project architecture. The VTON job service adds a new domain following established layer traversal: models → repositories → services → schemas → routers. Celery task layer runs separately as a worker process.

## Layer Structure

```text
┌─────────────────────────────────────┐
│      Presentation                   │  api/routers/vton.py
│      api/schemas/vton.py            │  Pydantic request/response
├─────────────────────────────────────┤
│      Application                    │  services/vton_job_service.py
│                                     │  services/providers/vton_provider.py
├─────────────────────────────────────┤
│        Domain                       │  models/vton_job.py (SQLAlchemy)
│                                     │  ClothType enum, JobStatus enum
├─────────────────────────────────────┤
│     Infrastructure                  │  repositories/vton_job_repo.py
│                                     │  tasks/vton_task.py (Celery)
│                                     │  core/celery_app.py (existing)
│                                     │  core/minio_client.py (from bolt 001)
└─────────────────────────────────────┘
```

## API Design

### Endpoints

| Endpoint | Method | Request | Response | Auth |
|----------|--------|---------|----------|------|
| `/api/vton/generate` | POST | JSON: `{ garment_photo_id, model_photo_id, cloth_type }` | `201` → `{ job_id, status: "queued", created_at }` | Required |
| `/api/vton/jobs/{job_id}` | GET | (path param) | `200` → `{ job_id, status, created_at, started_at?, completed_at?, result_url?, error_reason?, retry_count? }` | Required |

### Pydantic Schemas

```python
# api/schemas/vton.py

class ClothType(str, Enum):
    upper_body = "upper_body"
    lower_body = "lower_body"
    dress = "dress"

class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class VTONGenerateRequest(BaseModel):
    garment_photo_id: UUID
    model_photo_id: UUID
    cloth_type: ClothType

class VTONJobCreateResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created_at: datetime

class VTONJobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_url: str | None = None
    error_reason: str | None = None
    retry_count: int = 0
```

## Data Persistence

### Table: `vton_jobs`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default `uuid4()` |
| `mayorista_id` | UUID | FK → `mayorista.id` ON DELETE CASCADE, NOT NULL |
| `garment_photo_id` | UUID | FK → `garment_photos.id` ON DELETE RESTRICT, NOT NULL |
| `model_photo_id` | UUID | FK → `model_photos.id` ON DELETE SET NULL, NOT NULL |
| `cloth_type` | String(20) | NOT NULL, CHECK in ('upper_body', 'lower_body', 'dress') |
| `status` | String(20) | NOT NULL, default `'queued'`, CHECK in ('queued', 'processing', 'completed', 'failed') |
| `retry_count` | Integer | NOT NULL, default 0 |
| `max_retries` | Integer | NOT NULL, default from env `VTON_MAX_RETRIES` (default 3) |
| `error_reason` | Text | NULLABLE |
| `result_minio_key` | String(512) | UNIQUE, NULLABLE |
| `created_at` | DateTime | NOT NULL, server_default `now()` |
| `started_at` | DateTime | NULLABLE |
| `completed_at` | DateTime | NULLABLE |

**Indexes**
- `idx_vton_jobs_mayorista` on `vton_jobs(mayorista_id)`
- `idx_vton_jobs_mayorista_created` on `vton_jobs(mayorista_id, created_at DESC)`
- `idx_vton_jobs_status` on `vton_jobs(status)` WHERE `status IN ('queued', 'processing')`

## Celery Task Design

### Task: `tasks.vton_task.process_vton_job`

```python
@app.task(bind=True, name="tasks.vton_task.process_vton_job", max_retries=3, acks_late=True)
def process_vton_job(self, job_id: str) -> None:
    """Celery task that processes a single VTON job."""
    # 1. Re-read job from DB — confirm status=queued (idempotency guard)
    # 2. Update status → processing, set started_at
    # 3. Get garment and model presigned URLs from MinIO
    # 4. Call VTONProvider.generate(garment_url, model_url, cloth_type)
    # 5. Upload result to MinIO at results/{mayorista_id}/{job_id}.jpg
    # 6. Update status → completed, set result_minio_key, completed_at
    # On exception:
    #   - If retriable: self.retry() (handled by Celery)
    #   - If not retriable (4xx auth): mark failed immediately
```

**Queue**: `vton.generation.normal` (existing queue in `core/celery_app.py`)

**Idempotency**: Task re-reads job from DB at start. If status is not `queued`, worker skips (guard against duplicate RabbitMQ delivery).

**Provider injection**: `VTONProvider` implementation selected at worker startup via `VTON_PROVIDER` env var.

## VTONProvider Interface

```python
# services/providers/vton_provider.py

class VTONProvider(ABC):
    @abstractmethod
    async def generate(self, garment_url: str, model_url: str, cloth_type: str) -> bytes:
        """Run VTON inference and return generated image bytes."""

class LocalGPUProvider(VTONProvider):
    """Dev provider — calls local IDM-VTON service."""
    async def generate(self, garment_url, model_url, cloth_type):
        # Download images from presigned URLs
        # POST to settings.VTON_LOCAL_URL with multipart form data
        # Return response bytes

class ReplicateProvider(VTONProvider):
    """Prod provider — calls Replicate API."""
    async def generate(self, garment_url, model_url, cloth_type):
        # replicate.run(settings.CATVTON_REPLICATE_MODEL, input={...})
        # Download result URL to bytes
        # Return bytes
```

**Factory function**: `get_vton_provider() → VTONProvider` reads `settings.VTON_PROVIDER` and returns the correct implementation.

## Security Design

| Concern | Approach |
|---------|----------|
| Authentication | `Depends(get_current_mayorista)` on all endpoints |
| Authorization | All queries filtered by `mayorista_id` — mayorista can only see their own jobs |
| Photo ownership | `submit_job` validates `garment_photo_id` belongs to mayorista; `model_photo_id` can be own or curated |
| Input validation | Pydantic `ClothType` enum validates at request boundary |
| Error exposure | Failed jobs expose `error_reason` but never stack traces or internal details |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| Job submission < 500ms | Async API; DB insert + Celery `send_task` are fast; no blocking I/O |
| Inference < 60s (dev), < 120s (prod) | Provider abstraction; LocalGPU runs on same network; Replicate handles scaling |
| Failure rate < 5% | Retry logic in Celery (max_retries=3); bolt 003 adds exponential backoff |
| Poll response < 200ms | Simple DB read + optional presign; indexed by `(id, mayorista_id)` |

## Error Handling

| Error Type | HTTP Code | Response |
|------------|-----------|----------|
| Not authenticated | 401 | `{"detail": "Not authenticated"}` |
| Invalid cloth_type | 400 | Pydantic validation error |
| Garment not found | 404 | `{"detail": "Garment photo not found"}` |
| Model not found | 404 | `{"detail": "Model photo not found"}` |
| Garment belongs to another mayorista | 403 | `{"detail": "You do not own this garment photo"}` |
| Job not found | 404 | `{"detail": "Job not found"}` |
| Job belongs to another mayorista | 403 | `{"detail": "You do not own this job"}` |

Domain exceptions in `services/`:
- `VTONJobNotFoundError`
- `PhotoOwnershipError`
- `VTONProcessingError`

Routers catch these and translate to `HTTPException`.

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| RabbitMQ | Task queue for Celery | AMQP via `core/celery_app.py` |
| Celery Worker | Async inference execution | `tasks/vton_task.py` |
| VTONProvider | AI inference | Interface in `services/providers/` |
| MinIO | Result image storage | `core/minio_client.py` (from bolt 001) |
| PostgreSQL | Job state persistence | SQLAlchemy async |
| GarmentPhoto/ModelPhoto | Photo metadata validation | Repositories from bolt 001 |

## Files to Create/Modify

### New Files
1. `models/vton_job.py` — SQLAlchemy model: `VTONJob`, `ClothType` enum, `JobStatus` enum
2. `repositories/vton_job_repo.py` — `VTONJobRepo`
3. `services/vton_job_service.py` — `VTONJobService` (submit, get status, validate ownership)
4. `services/providers/vton_provider.py` — `VTONProvider` interface + `LocalGPUProvider` + `ReplicateProvider` + factory
5. `tasks/vton_task.py` — New Celery task `process_vton_job`
6. `api/schemas/vton.py` — Pydantic schemas
7. `api/routers/vton.py` — FastAPI router for `/api/vton/*`

### Modified Files
1. `models/__init__.py` — Export `VTONJob`
2. `main.py` — Register `vton_router`
3. `core/celery_app.py` — Add `tasks.vton_task` to `include` list
4. `core/config.py` — Add `VTON_MAX_RETRIES` setting
5. `alembic/versions/` — New migration for `vton_jobs` table

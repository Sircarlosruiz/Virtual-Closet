---
unit: 001-batch-job-service
bolt: 023-batch-job-service
stage: design
status: complete
created: 2026-06-04T00:00:00Z
---

# Technical Design - Batch Job Service

## Architecture Pattern

**Layered / Domain-Driven within FastAPI monolith** — Consistent with existing system architecture. The batch domain follows the established pattern: routers → services → repositories → models. This maintains the invariant that each layer only depends on the layer directly below it.

**Rationale**: The existing codebase uses this pattern successfully. Introducing a different architecture for one domain would create inconsistency and maintenance burden. The batch domain is well-contained and benefits from clear layer separation without needing full hexagonal architecture.

## Layer Structure

```text
┌───────────────────────────────────────────────────┐
│      Presentation (api/routers/batches.py)        │  POST /api/batches, GET /api/batches/{id}
│      Pydantic schemas (api/schemas/batches.py)    │  Request/Response validation
├───────────────────────────────────────────────────┤
│      Application (services/batch_submission.py)   │  BatchSubmissionService use case
│                                                  │  Atomic create + enqueue orchestration
├───────────────────────────────────────────────────┤
│        Domain (services/batch_domain.py)          │  BatchJob/BatchItem entities
│                                                  │  Status enums, validation rules
├───────────────────────────────────────────────────┤
│     Infrastructure (repositories/batch_repo.py)   │  SQLAlchemy async queries
│     Models (models/batch_job.py)                 │  ORM entities, migrations
└───────────────────────────────────────────────────┘
```

## API Design

### POST /api/batches
- **Method**: POST
- **Auth**: `Depends(get_current_mayorista)` — JWT cookie
- **Request Body**:
```json
{
  "name": "Colección Verano 2026",
  "items": [
    { "garment_id": "uuid", "model_id": "uuid", "cloth_type": "upper_body" },
    { "garment_id": "uuid", "model_id": "uuid", "cloth_type": "lower_body" }
  ]
}
```
- **Response** (201 Created):
```json
{
  "id": "uuid",
  "name": "Colección Verano 2026",
  "status": "in-progress",
  "total_items": 2,
  "completed_count": 0,
  "failed_count": 0,
  "created_at": "2026-06-04T00:00:00Z"
}
```
- **Errors**:
  - `400`: Empty items list or > 100 items
  - `403`: Garment/model doesn't belong to mayorista
  - `422`: Pydantic validation failure

### GET /api/batches/{batch_id}
- **Method**: GET
- **Auth**: `Depends(get_current_mayorista)`
- **Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Colección Verano 2026",
  "status": "in-progress",
  "total_items": 2,
  "completed_count": 0,
  "failed_count": 0,
  "created_at": "2026-06-04T00:00:00Z",
  "items": [
    {
      "id": "uuid",
      "garment_id": "uuid",
      "model_id": "uuid",
      "cloth_type": "upper_body",
      "status": "processing",
      "vton_job_id": "uuid",
      "error_message": null
    }
  ]
}
```
- **Errors**:
  - `404`: Batch not found
  - `403`: Batch belongs to different mayorista

## Data Persistence

### Table: `batch_jobs`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default uuid4 |
| `mayorista_id` | UUID | FK → mayorista.id, NOT NULL, CASCADE delete |
| `name` | VARCHAR(255) | NOT NULL |
| `status` | VARCHAR(20) | NOT NULL, default 'pending', CHECK constraint |
| `total_items` | INTEGER | NOT NULL, CHECK (1 <= total_items <= 100) |
| `completed_count` | INTEGER | NOT NULL, default 0 |
| `failed_count` | INTEGER | NOT NULL, default 0 |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, default now() |
| `completed_at` | TIMESTAMP WITH TIME ZONE | NULL |

**Indexes**:
- `idx_batch_jobs_mayorista` ON (`mayorista_id`)
- `idx_batch_jobs_mayorista_created` ON (`mayorista_id`, `created_at` DESC)

### Table: `batch_items`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default uuid4 |
| `batch_id` | UUID | FK → batch_jobs.id, NOT NULL, CASCADE delete |
| `garment_id` | UUID | NOT NULL |
| `model_id` | UUID | NOT NULL |
| `cloth_type` | VARCHAR(20) | NOT NULL, CHECK constraint |
| `vton_job_id` | UUID | FK → vton_jobs.id, NULL (set during enqueue) |
| `status` | VARCHAR(20) | NOT NULL, default 'pending', CHECK constraint |
| `error_message` | TEXT | NULL |
| `result_media_id` | UUID | NULL (FK to media_items, set later) |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, default now() |
| `completed_at` | TIMESTAMP WITH TIME ZONE | NULL |

**Indexes**:
- `idx_batch_items_batch` ON (`batch_id`)
- `idx_batch_items_vton_job` ON (`vton_job_id`) WHERE `vton_job_id IS NOT NULL`

### Migration Strategy
- New `batch_jobs` and `batch_items` tables
- Add `batch_item_id` column to `vton_jobs` table (nullable FK, backwards-compatible)
- Alembic migration: `alembic revision --autogenerate -m "add_batch_job_tables"`

## Security Design

| Concern | Approach |
|---------|----------|
| **Authentication** | JWT in HttpOnly cookie — existing `get_current_mayorista` dependency |
| **Authorization** | Mayorista scoping on all queries: `WHERE mayorista_id = :current_user_id` |
| **Input Validation** | Pydantic schemas enforce item count (1-100), valid cloth_type enum, UUID format |
| **Ownership Verification** | Service layer verifies each `garment_id` and `model_id` belongs to the authenticated mayorista before batch creation |
| **Data Isolation** | No cross-mayorista data leakage — all repository methods require `mayorista_id` parameter |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| **Performance** | `POST /api/batches` must respond < 500ms for 100 items. Achieved by: bulk INSERT via SQLAlchemy `session.add_all()`, async Celery task delegation (non-blocking), indexed queries on `mayorista_id` |
| **Atomicity** | `async with session.begin():` wraps all DB operations + Celery enqueue. On any failure, transaction rolls back — no partial records |
| **Scalability** | Pagination on list endpoints (`page`, `page_size` params). Max page_size = 100. Indexes support efficient mayorista-scoped queries |
| **Reliability** | Celery retry policy for task publishing. Idempotent batch creation (client-provided idempotency key optional for future) |

## Error Handling

| Error Type | HTTP Status | Response |
|------------|-------------|----------|
| `EmptyBatchError` | 400 | `{"detail": {"code": "EMPTY_BATCH", "message": "Batch must contain at least 1 item"}}` |
| `BatchSizeExceededError` | 400 | `{"detail": {"code": "BATCH_SIZE_EXCEEDED", "message": "Batch size exceeds maximum of 100 items"}}` |
| `MayoristaOwnershipError` | 403 | `{"detail": {"code": "OWNERSHIP_VIOLATION", "message": "Garment/model does not belong to authenticated mayorista"}}` |
| `BatchSubmissionError` | 503 | `{"detail": {"code": "SUBMISSION_FAILED", "message": "Batch submission failed, no records created", "context": {"reason": "..."}}}` |
| `BatchNotFoundError` | 404 | `{"detail": {"code": "BATCH_NOT_FOUND", "message": "Batch not found"}}` |

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| **VtonJobService** (existing) | Creates individual VTON jobs from batch items | Python function call — `VtonJobService.create_and_enqueue()` |
| **Celery / RabbitMQ** | Async task queue for VTON inference | Task publishing via `celery.send_task()` or direct task call |
| **PostgreSQL** | Persistent storage for batch records | SQLAlchemy async engine — existing `get_db` dependency |

## Integration Points

### VtonJob.batch_item_id (New FK)
```python
# models/vton_job.py — backwards-compatible addition
batch_item_id = Column(UUID(as_uuid=True), ForeignKey("batch_items.id"), nullable=True)
```

### BatchSubmissionService Flow
```python
async def create_and_submit(mayorista_id, name, pairings):
    async with session.begin():
        # 1. Validate ownership of all garments/models
        await _verify_ownership(mayorista_id, pairings)
        
        # 2. Create BatchJob + BatchItem records
        batch = BatchJob(...)
        items = [BatchItem(...) for p in pairings]
        session.add(batch)
        session.add_all(items)
        
        # 3. Enqueue VtonJobs (sets vton_job_id on each item)
        for item in items:
            vton_job = await vton_service.create_and_enqueue(item)
            item.vton_job_id = vton_job.id
        
        # 4. Update batch status to in-progress
        batch.status = BatchJobStatus.in_progress
        
        # 5. Commit (atomic)
```

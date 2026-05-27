---
unit: 001-media-service
bolt: 001-media-service
stage: design
status: complete
updated: 2026-05-26T23:10:00Z
---

# Technical Design - Media Service

## Architecture Pattern

**Layered / Domain-Driven within monolith** — Consistent with the existing project architecture. The media service adds a new domain following the established layer traversal: models → repositories → services → schemas → routers. No new architectural patterns introduced.

## Layer Structure

```text
┌─────────────────────────────┐
│      Presentation           │  api/routers/media.py
│      api/schemas/media.py   │  Pydantic request/response
├─────────────────────────────┤
│      Application            │  services/media_service.py
│                             │  services/model_library_service.py
├─────────────────────────────┤
│        Domain               │  (entities defined in models/)
│                             │  (validation in services/)
├─────────────────────────────┤
│     Infrastructure          │  repositories/media_repo.py
│                             │  core/minio_client.py (new)
│                             │  models/media.py (SQLAlchemy)
└─────────────────────────────┘
```

## API Design

### Endpoints

| Endpoint | Method | Request | Response | Auth |
|----------|--------|---------|----------|------|
| `/api/media/garments` | POST | `multipart/form-data`: `file` (JPG/PNG ≤10MB) | `201` → `{ id, presigned_url, filename, uploaded_at }` | Required |
| `/api/media/models` | POST | `multipart/form-data`: `file` (JPG/PNG ≤10MB), `label?` (string) | `201` → `{ id, presigned_url, label, is_curated, uploaded_at }` | Required |
| `/api/media/models/mine` | GET | Query: `page?`, `page_size?` | `200` → `{ items: [...], total, page, page_size }` | Required |
| `/api/media/models/curated` | GET | (none) | `200` → `{ items: [...] }` (no pagination) | Required |
| `/api/media/garments` | GET | Query: `page?`, `page_size?` | `200` → `{ items: [...], total, page, page_size }` | Required |

### Pydantic Schemas

```python
# api/schemas/media.py

class MediaUploadResponse(BaseModel):
    id: UUID
    presigned_url: str
    filename: str
    uploaded_at: datetime

class ModelUploadResponse(BaseModel):
    id: UUID
    presigned_url: str
    label: str
    is_curated: bool
    uploaded_at: datetime

class ModelPhotoResponse(BaseModel):
    id: UUID
    label: str
    presigned_url: str
    is_curated: bool

class GarmentPhotoResponse(BaseModel):
    id: UUID
    presigned_url: str
    filename: str
    uploaded_at: datetime

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
```

## Data Persistence

### Tables

**`garment_photos`**

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default `uuid4()` |
| `mayorista_id` | UUID | FK → `mayorista.id` ON DELETE CASCADE, NOT NULL |
| `minio_key` | String(512) | UNIQUE, NOT NULL |
| `filename` | String(255) | NOT NULL |
| `content_type` | String(50) | NOT NULL |
| `size_bytes` | Integer | NOT NULL, CHECK > 0 |
| `uploaded_at` | DateTime | NOT NULL, server_default `now()` |

**`model_photos`**

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default `uuid4()` |
| `mayorista_id` | UUID | FK → `mayorista.id` ON DELETE SET NULL, NULLABLE |
| `minio_key` | String(512) | UNIQUE, NOT NULL |
| `label` | String(255) | NOT NULL |
| `is_curated` | Boolean | NOT NULL, default `False` |
| `content_type` | String(50) | NOT NULL |
| `size_bytes` | Integer | NOT NULL, CHECK > 0 |
| `uploaded_at` | DateTime | NOT NULL, server_default `now()` |

**Indexes**
- `idx_garment_photos_mayorista` on `garment_photos(mayorista_id)`
- `idx_garment_photos_mayorista_created` on `garment_photos(mayorista_id, uploaded_at)`
- `idx_model_photos_mayorista` on `model_photos(mayorista_id)` WHERE `mayorista_id IS NOT NULL`
- `idx_model_photos_curated` on `model_photos(is_curated)` WHERE `is_curated = true`

### SQLAlchemy Model Design

```python
# models/media.py
# Two SQLAlchemy models: GarmentPhoto, ModelPhoto
# Both inherit from Base (imported from models.mayorista)
# Use async-compatible column types
```

## MinIO Integration Design

### New File: `core/minio_client.py`

A shared async MinIO client using `aiobotocore`:

```python
class MinIOClient:
    async def upload_file(self, bucket: str, key: str, data: bytes, content_type: str) -> None
    async def get_presigned_url(self, bucket: str, key: str, expires: int = 900) -> str
    async def file_exists(self, bucket: str, key: str) -> bool
```

- `expires` defaults to 900 seconds (15 minutes)
- Bucket names from `settings.MINIO_BUCKET_*`
- Garment photos → `MINIO_BUCKET_ORIGINALS` under `garments/{mayorista_id}/{uuid}.{ext}`
- Model photos → `MINIO_BUCKET_ORIGINALS` under `models/{mayorista_id}/{uuid}.{ext}` or `models/curated/{uuid}.{ext}`

### File Validation

Validation happens **before** MinIO write in the service layer:

1. Read first bytes to detect MIME type via `python-magic` (magic bytes, not extension)
2. Allow only `image/jpeg` and `image/png`
3. Check `size_bytes ≤ 10 * 1024 * 1024` (10MB)
4. Reject zero-byte files

## Security Design

| Concern | Approach |
|---------|----------|
| Authentication | `Depends(get_current_mayorista)` on all endpoints — JWT from HttpOnly cookie |
| Authorization | All queries filtered by `mayorista_id` — mayorista can only see their own uploads |
| Curated access | `list_curated_models()` returns all curated models (no mayorista filter needed) |
| Upload to curated | No endpoint allows mayorista to upload to curated — returns 403 if attempted |
| File validation | Magic bytes check prevents disguised file types |
| MinIO access | Server-side only — mayoristas never get direct MinIO credentials |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| Upload response < 500ms | Async MinIO upload via `aiobotocore`; no blocking I/O |
| Pre-signed URL 15 min TTL | Hardcoded `expires=900` in `get_presigned_url()` |
| Mayorista isolation | Every query includes `WHERE mayorista_id = :id`; FK constraints enforce referential integrity |
| File size limit | Checked in service layer before any MinIO write — fails fast |

## Error Handling

| Error Type | HTTP Code | Response |
|------------|-----------|----------|
| Not authenticated | 401 | `{"detail": "Not authenticated"}` |
| Invalid file type | 400 | `{"detail": "Only JPG and PNG files are accepted"}` |
| File too large | 400 | `{"detail": "File size exceeds 10MB limit"}` |
| Empty file | 400 | `{"detail": "File is empty"}` |
| Garment/Model not found | 404 | `{"detail": "Photo not found"}` |
| Attempt curated upload | 403 | `{"detail": "Curated library is read-only"}` |

Domain exceptions in `services/`:
- `InvalidFileTypeError`
- `FileTooLargeError`
- `EmptyFileError`
- `MediaNotFoundError`

Routers catch these and translate to `HTTPException`.

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| MinIO | File storage for garment and model photos | `aiobotocore` async S3 client |
| PostgreSQL | Metadata persistence for `GarmentPhoto` and `ModelPhoto` | SQLAlchemy async via `core/database.py` |
| Auth (pre-condition) | Mayorista identity from JWT | `Depends(get_current_mayorista)` from `core/dependencies.py` |

## Files to Create/Modify

### New Files
1. `models/media.py` — SQLAlchemy models: `GarmentPhoto`, `ModelPhoto`
2. `repositories/media_repo.py` — `GarmentPhotoRepo`, `ModelPhotoRepo`
3. `services/media_service.py` — `MediaUploadService` (upload garment + model)
4. `services/model_library_service.py` — `ModelLibraryService` (list curated, list own, presigned URLs)
5. `api/schemas/media.py` — Pydantic request/response schemas
6. `api/routers/media.py` — FastAPI router for `/api/media/*`
7. `core/minio_client.py` — Async MinIO client wrapper

### Modified Files
1. `models/__init__.py` — Export `GarmentPhoto`, `ModelPhoto`
2. `main.py` — Register `media_router`
3. `core/minio_buckets.py` — Add bucket names if new buckets needed (reusing `originals`)
4. `alembic/versions/` — New migration for `garment_photos` and `model_photos` tables

---
unit: 001-catalog-service
bolt: 006-catalog-service
stage: design
status: complete
updated: 2026-05-28T11:00:00Z
---

# Technical Design - 001-catalog-service

## Architecture Pattern

**Layered Domain-Driven** — consistent with the existing backend architecture. Each domain traverses all layers: Model → Repository → Service → Schema → Router. The catalog domain follows the same pattern as `vton_job` and `prenda`.

**Rationale**: The existing codebase uses a proven layered pattern. Introducing a different architecture (hexagonal, CQRS) for a single domain would create inconsistency without sufficient complexity justification.

## Layer Structure

```text
┌─────────────────────────────────────────────────────────────┐
│  Presentation — api/routers/catalogo.py                     │
│  HTTP endpoints, auth dependency, error mapping             │
├─────────────────────────────────────────────────────────────┤
│  DTOs — api/schemas/catalogo.py                             │
│  Pydantic request/response models                           │
├─────────────────────────────────────────────────────────────┤
│  Application — services/catalogo_service.py                 │
│  Business logic, orchestration, domain exceptions           │
├─────────────────────────────────────────────────────────────┤
│  Data Access — repositories/catalogo_repo.py                │
│  AsyncSession queries, CRUD operations                      │
├─────────────────────────────────────────────────────────────┤
│  Domain — models/catalogo.py                                │
│  SQLAlchemy ORM entities: Catalogo, CatalogoItem            │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure — core/minio_client.py (existing)           │
│  Pre-signed URL generation for image_key                    │
└─────────────────────────────────────────────────────────────┘
```

## File Manifest

1 - `backend/models/catalogo.py` — Catalogo + CatalogoItem ORM models
2 - `backend/repositories/catalogo_repo.py` — CatalogoRepo + CatalogoItemRepo
3 - `backend/services/catalogo_service.py` — CatalogoService + domain exceptions
4 - `backend/api/schemas/catalogo.py` — Pydantic request/response DTOs
5 - `backend/api/routers/catalogo.py` — APIRouter with endpoints
6 - `backend/main.py` — Register `catalogo_router`
7 - `backend/models/__init__.py` — Add Catalogo, CatalogoItem exports
8 - `backend/alembic/versions/` — Migration for `catalogo` + `catalogo_item` tables

## API Design

### POST /api/catalogos — Create Catalog

**Request**:
```json
{
  "name": "Summer 2026"
}
```

**Response** (201):
```json
{
  "id": "uuid",
  "name": "Summer 2026",
  "status": "draft",
  "item_count": 0,
  "created_at": "2026-05-28T10:00:00Z"
}
```

**Errors**: 400 (name validation), 401 (not authenticated)

---

### POST /api/catalogos/{catalog_id}/items — Add Item

**Request**:
```json
{
  "vton_job_id": "uuid",
  "garment_name": "Linen Blazer",
  "price": "89.99",
  "cloth_type": "upper_body",
  "sku": "LBZ-001"
}
```

**Response** (201):
```json
{
  "id": "uuid",
  "catalog_id": "uuid",
  "vton_job_id": "uuid",
  "image_url": "https://minio.../presigned...",
  "garment_name": "Linen Blazer",
  "price": "89.99",
  "cloth_type": "upper_body",
  "sku": "LBZ-001",
  "position": 1,
  "created_at": "2026-05-28T10:00:00Z"
}
```

**Errors**: 400 (validation), 403 (ownership mismatch), 404 (job/catalog not found), 422 (job not completed)

---

### DELETE /api/catalogos/{catalog_id}/items/{item_id} — Remove Item

**Response** (204): No body

**Errors**: 403 (ownership), 404 (catalog/item not found)

---

### PATCH /api/catalogos/{catalog_id}/items/reorder — Reorder Items

**Request**:
```json
{
  "ordered_item_ids": ["uuid3", "uuid1", "uuid2"]
}
```

**Response** (200):
```json
{
  "items": [
    { "id": "uuid3", "position": 1, "garment_name": "...", "image_url": "...", "price": "...", "cloth_type": "...", "sku": "..." },
    { "id": "uuid1", "position": 2, "garment_name": "...", "image_url": "...", "price": "...", "cloth_type": "...", "sku": "..." },
    { "id": "uuid2", "position": 3, "garment_name": "...", "image_url": "...", "price": "...", "cloth_type": "...", "sku": "..." }
  ]
}
```

**Errors**: 400 (bijection violation, duplicates, empty array), 403 (ownership), 404 (catalog not found)

## Data Model

### Table: `catalogo`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, `default=uuid4` | |
| `mayorista_id` | `UUID` | FK→`mayorista.id` ON DELETE CASCADE, NOT NULL | |
| `name` | `String(100)` | NOT NULL | Max 100 chars |
| `status` | `String(20)` | NOT NULL, default="draft", CheckConstraint IN ('draft','published') | |
| `item_count` | `Integer` | NOT NULL, default=0 | Denormalized counter |
| `created_at` | `DateTime(tz)` | NOT NULL, `server_default=now()` | |
| `updated_at` | `DateTime(tz)` | NOT NULL, `server_default=now()`, `onupdate=now()` | |

**Indexes**:
- `idx_catalogo_mayorista` on `(mayorista_id)`
- `idx_catalogo_mayorista_created` on `(mayorista_id, created_at)`

### Table: `catalogo_item`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, `default=uuid4` | |
| `catalog_id` | `UUID` | FK→`catalogo.id` ON DELETE CASCADE, NOT NULL | |
| `vton_job_id` | `UUID` | FK→`vton_jobs.id` ON DELETE RESTRICT, NOT NULL | |
| `garment_name` | `String(200)` | NOT NULL | |
| `price` | `Numeric(10,2)` | NOT NULL | |
| `cloth_type` | `String(20)` | NOT NULL, CheckConstraint IN ('upper_body','lower_body','dress') | |
| `sku` | `String(100)` | NOT NULL | |
| `image_key` | `String(512)` | NOT NULL | MinIO object key from VTON result |
| `position` | `Integer` | NOT NULL | Display order |
| `created_at` | `DateTime(tz)` | NOT NULL, `server_default=now()` | |

**Indexes**:
- `idx_catalogo_item_catalog` on `(catalog_id)`
- `idx_catalogo_item_catalog_position` on `(catalog_id, position)`
- Unique constraint on `(catalog_id, position)`

## Security Design

- **Authentication**: `Depends(get_current_mayorista)` on all endpoints — cookie-based JWT (existing pattern)
- **Authorization**: Every query filters by `mayorista_id` from the JWT. Catalog queries use `get_by_id_and_mayorista`. Item operations verify parent catalog ownership first.
- **Cross-mayorista item add**: Service validates both catalog ownership AND VTON job ownership before creating item. Returns 403 if either check fails.
- **Input validation**: Pydantic schemas enforce name length, price non-negative, cloth_type enum, non-empty arrays.

## NFR Implementation

- **Performance (p95 < 300ms)**:
  - `item_count` denormalized to avoid COUNT on catalog reads
  - Composite index `(catalog_id, position)` for ordered item queries
  - Reorder uses batch UPDATE within single transaction
- **Atomicity**: Reorder wrapped in single DB transaction — all position updates or none
- **Pre-signed URLs**: Generated on-demand via existing `MinIOClient.get_presigned_url()` — `image_key` stored, URL never persisted

## Error Handling

### Domain Exceptions (in `services/catalogo_service.py`)

```python
class CatalogoNotFoundError(Exception):
    """Catalog does not exist or not owned by requesting mayorista."""

class CatalogoItemNotFoundError(Exception):
    """Catalog item does not exist in the specified catalog."""

class CatalogoOwnershipError(Exception):
    """Mayorista does not own the referenced catalog."""

class VTONJobNotCompletedError(Exception):
    """VTON job must be completed before adding to catalog."""

class VTONJobOwnershipError(Exception):
    """VTON job does not belong to the requesting mayorista."""

class ReorderValidationError(Exception):
    """Reorder request does not contain exact bijection of catalog items."""
```

### Error → HTTP Mapping (in `api/routers/catalogo.py`)

1 - `CatalogoNotFoundError` → 404
2 - `CatalogoItemNotFoundError` → 404
3 - `CatalogoOwnershipError` → 403
4 - `VTONJobOwnershipError` → 403
5 - `VTONJobNotCompletedError` → 422
6 - `ReorderValidationError` → 400

## External Dependencies

- **VTONJobRepo** (read-only): `get_by_id()`, `get_by_id_and_mayorista()` — validates job exists, is completed, and belongs to same mayorista. Uses existing `repositories/vton_job_repo.py`.
- **MinIOClient** (existing): `get_presigned_url(bucket, key)` — generates pre-signed URL from `image_key` for item responses. Uses existing `core/minio_client.py`.
- **VTONJob model**: Read `result_minio_key` field to populate `image_key` on CatalogoItem creation.

## Integration Points

### VTON Job Cross-Reference (Read-Only)

When adding an item, the service:
1. Queries `VTONJob` by `vton_job_id`
2. Validates `job.status == "completed"` → else raise `VTONJobNotCompletedError`
3. Validates `job.mayorista_id == requesting_mayorista_id` → else raise `VTONJobOwnershipError`
4. Reads `job.result_minio_key` → stored as `CatalogoItem.image_key`

### MinIO Pre-Signed URL Generation

When returning items, the service:
1. Reads `CatalogoItem.image_key`
2. Calls `MinIOClient.get_presigned_url("generated", image_key)`
3. Includes `image_url` in the response DTO

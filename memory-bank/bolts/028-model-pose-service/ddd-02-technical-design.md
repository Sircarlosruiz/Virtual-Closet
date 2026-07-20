---
unit: 001-model-pose-service
bolt: 028-model-pose-service
stage: design
status: complete
updated: 2026-07-18T04:10:25Z
---

# Technical Design - Model Pose Service

## Architecture Pattern

**Layered DDD** per project coding standards — the domain traverses all layers top-to-bottom:

1. `models/model.py` (new) + `models/media.py` `ModelPhoto` (extended) → SQLAlchemy ORM entities
2. `repositories/model_repo.py` (new) + reuse/extend `repositories/media_repo.py` → data access
3. `services/model_pose_service.py` (new) → business logic, no FastAPI dependency; delegates file validation + MinIO writes to existing `services/media_service.py`
4. `api/schemas/models.py` (new) + `api/routers/models.py` (new) → Pydantic DTOs + HTTP endpoints
5. Register router in `main.py`; generate Alembic migration

*Rationale*: matches the established pattern from `001-media-service` and ADR-006's precedent for backwards-compatible cross-domain table extension. The unit brief's "Django" references are superseded by the actual project stack (FastAPI + SQLAlchemy + Alembic per `tech-stack.md` / `coding-standards.md`).

## Layer Structure

```text
┌─────────────────────────────────────────────┐
│  Presentation   api/routers/models.py       │  HTTP, auth dep, HTTPException translation
├─────────────────────────────────────────────┤
│  Application    api/schemas/models.py       │  Pydantic request/response DTOs
├─────────────────────────────────────────────┤
│  Domain         services/model_pose_service │  create_model / upload_pose / list_poses
│                 + domain exceptions         │  ModelNotFoundError, DuplicatePoseError
├─────────────────────────────────────────────┤
│  Infrastructure repositories/model_repo.py  │  SQLAlchemy queries (AsyncSession)
│                 services/media_service.py   │  (existing) file validation + MinIO
└─────────────────────────────────────────────┘
```

## API Design

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/models` | `POST` | JSON `{name: str}` (1–255 chars, trimmed) | `201` `ModelResponse {id, mayorista_id, name, created_at}` |
| `/api/models/{model_id}/poses` | `POST` | `multipart/form-data`: `file` (JPG/PNG ≤10MB), `pose` (`front`\|`side`\|`back`) | `201` `PosePhotoResponse {id, model_id, pose, image_url, uploaded_at}` (`image_url` = presigned, 15-min TTL) |
| `/api/models/{model_id}/poses` | `GET` | — | `200` `{items: [PosePhotoResponse], total: int}` ordered `front, side, back` |

**Notes**:
- Auth via HttpOnly JWT cookie; `mayorista_id` from `Depends(get_current_mayorista)` — never from request input.
- List endpoint returns the standard `{items, total}` envelope but **no page params**: the list is inherently bounded (≤3 poses/model), so it is never unbounded. Pagination explicitly out of scope per story 003.
- Pose ordering implemented at query time (`CASE pose WHEN 'front' THEN 0 WHEN 'side' THEN 1 WHEN 'back' THEN 2 END`) — deterministic regardless of insertion order.

## Data Persistence

| Table | Columns | Relationships |
|-------|---------|---------------|
| `models` (new) | `id` UUID PK, `mayorista_id` UUID NOT NULL, `name` VARCHAR(255) NOT NULL, `created_at` TIMESTAMPTZ NOT NULL DEFAULT now() | `mayorista_id` FK → `mayoristas.id` |
| `model_photos` (extended) | *(existing)* `id`, `mayorista_id`, `minio_key`, `is_curated`, `uploaded_at`; *(new)* `model_id` UUID NULL, `pose` VARCHAR(10) NULL | `model_id` FK → `models.id` ON DELETE CASCADE (aggregate ownership) |

**Migration (Alembic)**:
1. Create `models` table (+ index on `mayorista_id`).
2. `model_photos`: add nullable `model_id` column (+ index) — existing rows stay `NULL` per ADR-006 pattern.
3. `model_photos`: add nullable `pose` column.
4. Add `UNIQUE (model_id, pose)` constraint `uq_model_photos_model_pose` — PostgreSQL allows multiple NULLs, so curated rows are unaffected (ADR-010 pattern).
5. Add `CHECK (pose IN ('front','side','back'))` and `CHECK ((model_id IS NULL) = (pose IS NULL))` — DB-enforced invariant: a photo is either a curated/legacy row (both NULL) or a pose photo (both set).

## Security Design

| Concern | Approach |
|---------|----------|
| Authentication | Custom JWT in HttpOnly cookie (`access_token`); protected routes use `Depends(get_current_mayorista)` → 401 when absent/invalid |
| Authorization | Ownership enforced at repository level: every query filters by `mayorista_id` from the session. Unowned/nonexistent model → **404, never 403** (no existence leak, per story 003 edge case) |
| Input validation | Pydantic on DTOs (`name` length, `pose` literal); file type/size via existing media validation (JPG/PNG ≤10MB) |
| Data protection | Presigned URLs (15-min TTL) generated per request, never persisted, **never logged** (embedded credentials) |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| Performance | Bounded result sets (≤3 poses); indexed lookups on `models.mayorista_id`, `model_photos.model_id`; single-query list with `CASE` ordering |
| Scalability | Stateless endpoints; storage/load unchanged from existing media path (MinIO) |
| Reliability | DB unique constraint on `(model_id, pose)` is the authoritative duplicate guard under concurrent uploads; app-level `pose_exists` fast-path for clean 400s; `IntegrityError` → mapped to `DuplicatePoseError` → 400 |

## Error Handling

| Error Type | Code | Response |
|------------|------|----------|
| Missing/invalid `name` | `VALIDATION_ERROR` | `400`/`422` (Pydantic) |
| `pose` outside enum | `VALIDATION_ERROR` | `400`/`422` (Pydantic) |
| Model not found or unowned | `MODEL_NOT_FOUND` | `404 {"detail": "Model not found"}` |
| Duplicate pose type on model | `DUPLICATE_POSE` | `400 {"detail": "Pose type already exists for this model"}` |
| Invalid file type / >10MB | (existing media validation) | `400` per existing `001-media-service` behavior |
| Not authenticated | — | `401` |

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| `services/media_service.py` (existing) | File type/size validation, MinIO write, presigned URL generation | Internal Python call — reused as-is, no modification to garment upload behavior |
| MinIO | Pose photo object storage under mayorista namespace | S3 API (existing client) |
| PostgreSQL | `models` + extended `model_photos` persistence | SQLAlchemy async + Alembic migration |

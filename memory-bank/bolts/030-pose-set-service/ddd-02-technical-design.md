---
unit: 002-pose-set-service
bolt: 030-pose-set-service
stage: design
status: complete
updated: 2026-07-18T06:47:24Z
---

# Technical Design - Pose Set Service

## Architecture Pattern

Layered DDD over the existing FastAPI + SQLAlchemy async stack:

1. `models/pose_set.py` — PoseSet ORM entity
2. `repositories/pose_set_repo.py` — ownership-scoped PoseSet and joined result queries
3. `services/pose_set_service.py` — validation, transaction orchestration, status projection
4. `api/schemas/pose_sets.py` + `api/routers/pose_sets.py` — REST contract
5. Existing `BatchSubmissionService` — reused for BatchJob/BatchItem/VTON job creation

The service must not implement a second batch path. It calls the existing batch
creation service with a `BatchCreateRequest` built from selected ModelPhoto IDs.

## Layer Structure

```text
┌─────────────────────────────────────────────┐
│ Presentation  api/routers/pose_sets.py      │  auth, HTTP errors, DTOs
├─────────────────────────────────────────────┤
│ Application   services/pose_set_service.py  │  validate + orchestrate + project
├─────────────────────────────────────────────┤
│ Domain        PoseSet + selection rules     │  aggregate invariants
├─────────────────────────────────────────────┤
│ Infrastructure PoseSetRepo + existing batch │  SQLAlchemy, media URLs, Celery path
└─────────────────────────────────────────────┘
```

## API Design

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/pose-sets` | `POST` | JSON `{garment_id, model_id, cloth_type, pose_ids: UUID[]}` | `201 {pose_set_id, batch_id, total_items}` |
| `/api/pose-sets/{pose_set_id}` | `GET` | — | `200 {pose_set_id, garment_id, model_id, status, items[]}` |

`pose_ids` is validated as non-empty and duplicate-free. Duplicate IDs return
400 rather than silently changing the submitted selection. Invalid or
cross-model IDs return 400 with no persisted records.

## Data Persistence

### New `pose_sets` table

| Column | Definition |
|--------|------------|
| `id` | UUID primary key |
| `mayorista_id` | UUID NOT NULL, FK to `mayorista.id` with CASCADE |
| `tenant_id` | UUID NOT NULL, FK to `tenants.id` with CASCADE, matching current platform tenancy |
| `model_id` | UUID NOT NULL, FK to `models.id` with CASCADE |
| `garment_id` | UUID NOT NULL, FK to `garment_photos.id` with CASCADE |
| `batch_id` | UUID NOT NULL, FK to `batch_jobs.id` with CASCADE, UNIQUE |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() |

Indexes: `(mayorista_id, created_at DESC)`, `tenant_id`, `batch_id` (unique),
and `model_id`.

### Existing tables

- `batch_jobs` and `batch_items` are created through the existing batch service.
- Each `BatchItem.model_id` stores the selected `ModelPhoto.id`, allowing result
  projection to resolve `ModelPhoto.pose`.
- No changes to VTON execution, retry, or media-save logic.

### Tenant integration constraint

`BatchJob.tenant_id` is currently non-nullable, but the existing
`BatchSubmissionService` constructor path does not populate it. The internal
batch creation contract must accept `tenant_id` and set it on the BatchJob;
the public batch endpoint should pass the authenticated mayorista's tenant.
This is a small compatibility fix to the existing service, not duplicated batch
logic, and is required before PoseSet submissions can persist successfully.

## Transaction and Atomicity Design

The router obtains one `AsyncSession`. `PoseSetSubmissionService` performs:

1. Resolve and validate mayorista tenant context.
2. Fetch the garment ownership-scoped.
3. Fetch all requested ModelPhoto rows with one query constrained by
   `model_id`, `mayorista_id`, and `pose_ids`.
4. Reject if the set is empty, contains duplicates, or does not match every
   requested ID.
5. Build the existing `BatchCreateRequest` with one item per selected
   ModelPhoto (`model_id=ModelPhoto.id`).
6. Call existing `BatchSubmissionService.create_and_submit(..., db=session)`.
7. Add PoseSet with the returned BatchJob ID and flush.
8. Commit once. On any exception, rollback the session and persist neither
   PoseSet nor BatchJob/BatchItems.

The existing batch service currently creates VTON jobs during the transaction;
its existing post-commit enqueue behavior and ADR-005/ADR-007 rules remain the
single source of truth for task publication.

## Result Projection

`PoseSetRepo.get_with_results(pose_set_id, mayorista_id)` joins:

`PoseSet → BatchJob → BatchItem → ModelPhoto`, with optional
`BatchItem.result_media_id → MediaItem`.

The service maps:

- `ModelPhoto.pose` → `pose_type`
- `BatchItem.id` → `batch_item_id`
- `BatchItem.result_media_id` → `media_id`
- existing BatchItem status → item status
- `BatchItem.error_message` → item error
- existing MinIO/media service → fresh presigned `image_url`

Set status is derived from BatchJob status. If item outcomes are mixed, the
projection reports `partial` consistently with the story, even when an older
BatchJob status has not yet been recalculated.

## Security Design

| Concern | Approach |
|---------|----------|
| Authentication | Existing JWT cookie dependency `get_current_mayorista` |
| Authorization | Every PoseSet, garment, ModelPhoto, Model, and batch lookup is scoped by mayorista and tenant |
| Resource leakage | Missing and unowned PoseSets return 404, not 403 |
| Result media | Presigned URLs generated only after ownership-scoped result lookup; URLs are never logged |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| Submission latency | One pose validation query + existing batch persistence; no inference in request; target <500ms for ≤3 poses |
| Atomicity | One SQLAlchemy session transaction; PoseSet flush occurs before commit; rollback on all failures |
| Read performance | Indexed PoseSet ownership/batch joins; maximum three pose items per set; eager-load batch items and media metadata |
| Scalability | Reuse existing BatchJob/Celery pipeline; no new worker or polling infrastructure |

## Error Handling

| Error Type | Code | Response |
|------------|------|----------|
| Empty `pose_ids` | `400` | `{"detail": "At least one pose must be selected"}` |
| Duplicate pose IDs | `400` | `{"detail": "Duplicate poses are not allowed"}` |
| ID not in requested Model | `400` | `{"detail": "All poses must belong to the selected model"}` |
| Garment/model ownership failure | `403` or generic `404` | Match existing batch ownership behavior; do not create records |
| PoseSet missing/unowned | `404` | `{"detail": "Pose set not found"}` |
| Delegated batch failure | `503` | Rollback session; no PoseSet or batch records persist |

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| Existing `BatchSubmissionService` | BatchJob/BatchItem/VTON job creation | Internal Python call with shared AsyncSession |
| Existing `ModelPhotoRepo` | Validate selected poses and resolve pose type | SQLAlchemy query |
| Existing `MediaLibraryService` | Result media lookup and presigned URLs | Internal Python call |
| PostgreSQL | PoseSet and existing batch persistence | SQLAlchemy async + Alembic |

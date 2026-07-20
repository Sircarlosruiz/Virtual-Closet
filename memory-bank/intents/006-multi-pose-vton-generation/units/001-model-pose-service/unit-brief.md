---
unit: 001-model-pose-service
intent: 006-multi-pose-vton-generation
phase: inception
status: complete
unit_type: backend
default_bolt_type: ddd-construction-bolt
created: 2026-07-17T00:00:00.000Z
updated: 2026-07-17T00:00:00.000Z
---

# Unit Brief: model-pose-service

## Purpose

Backend domain owning the `Model` identity concept: a named grouping of 1..N `ModelPhoto` pose photos, each tagged with a fixed pose type. Exposes model/pose CRUD and one-time backfills legacy `ModelPhoto` rows (created before this intent) into implicit single-pose `Model` wrappers so no mayorista-facing data is lost.

## Scope

### In Scope
- `Model` aggregate (Django model) and extension of existing `ModelPhoto` with `model_id` FK and `pose` enum field
- `POST /api/models` — create a `Model`
- `POST /api/models/{model_id}/poses` — upload a pose photo tagged with a pose type; rejects duplicate pose type or unowned model
- `GET /api/models/{model_id}/poses` — list poses with pre-signed URLs
- One-time backfill migration: every pre-existing mayorista-owned `ModelPhoto` (not curated) gets wrapped in a new `Model` with a single `front`-tagged pose

### Out of Scope
- Curated model library (`is_curated=true` `ModelPhoto` rows are untouched, no `Model` parent required)
- Pose-aware submission / batch expansion (handled by `002-pose-set-service`)
- Frontend UI (handled by `003-multi-pose-vton-generation-ui`)
- New file storage mechanism (reuses existing MinIO upload path from `001-media-service`)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Model entity + pose photo upload with fixed enum, no duplicate pose types, min 1 pose | Must |
| FR-2 | List all poses for a model, mayorista-scoped | Must |
| FR-7 | Backfill legacy `ModelPhoto` rows into implicit single-pose `Model` wrappers | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `Model` | A named model identity owned by a mayorista, grouping 1..N poses | `id`, `mayorista_id`, `name`, `created_at` |
| `ModelPhoto` (extended) | A single pose photo belonging to a `Model` (existing entity from `001-media-service`, extended) | `id`, `model_id` (nullable — null for curated), `mayorista_id`, `minio_key`, `pose` (enum: `front`\|`side`\|`back`, nullable for curated), `is_curated`, `uploaded_at` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `create_model` | Creates a new `Model` for the mayorista | `mayorista_id`, `name` | `Model` |
| `upload_pose` | Validates pose type not already used on this model, delegates file validation/MinIO write to existing media upload path, creates `ModelPhoto` linked to `Model` | `model_id`, `mayorista_id`, file bytes, `pose` | `ModelPhoto` + presigned URL |
| `list_poses` | Returns all poses for a model, mayorista-scoped | `model_id`, `mayorista_id` | list of `ModelPhoto` with presigned URLs |
| `backfill_legacy_models` | One-time migration: wraps each pre-existing non-curated `ModelPhoto` in a new single-pose `Model` | (none — run once) | `Model` + `ModelPhoto.model_id`/`pose` updated for all legacy rows |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 4 |
| Must Have | 4 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-create-model | Create Model Identity | Must | Planned |
| 002-upload-pose-photo | Upload Pose Photo with Fixed Enum Validation | Must | Planned |
| 003-list-model-poses | List Poses for a Model | Must | Planned |
| 004-backfill-legacy-models | Backfill Legacy ModelPhoto Rows into Models | Must | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `001-media-service` (intent `001-vton-generation-pipeline`) | Reuses file type/size validation and MinIO upload conventions |

### Depended By

| Unit | Reason |
|------|--------|
| `002-pose-set-service` | Reads a model's poses to expand a pose-aware submission |
| `003-multi-pose-vton-generation-ui` | Consumes model/pose CRUD endpoints |

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| MinIO | Pose photo storage (existing infra) | Low |
| PostgreSQL | `Model`/`ModelPhoto` metadata persistence | Low |

---

## Technical Context

### Suggested Technology
- Extend existing `models/media.py` `ModelPhoto` with `model_id` FK + `pose` enum column (migration)
- New `Model` Django model in the same app as `ModelPhoto`
- Reuse `services/media_service.py` upload/validation functions for pose file handling
- New router endpoints in `api/routers/media.py` (or a new `models.py` router if preferred by Construction)

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| Existing media upload/validation service | Internal service call | Python function call |
| MinIO | File storage | S3 API (boto3 / minio-py) |
| PostgreSQL | Metadata persistence | SQLAlchemy/Django ORM |

### Data Storage

| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| `Model` records | PostgreSQL | Low (per mayorista) | Permanent |
| `ModelPhoto` records (extended) | PostgreSQL | Low-Medium (≤3 per Model) | Permanent |

---

## Constraints

- Pose enum is fixed: `front`, `side`, `back` — no arbitrary labels, no more than 3 poses per model
- A pose type can be used at most once per `Model`
- A `Model` must have at least 1 pose at all times
- Backfill migration must be idempotent and lossless — every legacy `ModelPhoto` maps to exactly one new `Model`
- Curated `ModelPhoto` rows (`is_curated=true`) are excluded from backfill and remain `model_id=null`
- Must not modify existing `001-media-service` garment upload behavior

---

## Success Criteria

### Functional
- [ ] Mayorista can create a `Model` and upload up to 3 poses tagged `front`/`side`/`back`
- [ ] Duplicate pose type on the same model is rejected with 400
- [ ] Mayorista can list all poses for their model with working presigned URLs
- [ ] Every pre-existing `ModelPhoto` has a `Model` parent after backfill runs, with zero data loss

### Non-Functional
- [ ] Pose upload follows existing file validation (JPG/PNG, ≤10MB)
- [ ] Presigned URLs expire after 15 minutes (existing convention)
- [ ] A mayorista cannot access another mayorista's models or poses

### Quality
- [ ] Code coverage > 80%
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 028-model-pose-service | ddd-construction-bolt | 001, 002, 003 | `Model`/`ModelPhoto` domain model + pose CRUD API |
| 029-model-pose-service | ddd-construction-bolt | 004 | Legacy `ModelPhoto` backfill migration |

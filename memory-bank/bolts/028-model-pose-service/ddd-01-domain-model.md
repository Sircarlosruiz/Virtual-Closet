---
unit: 001-model-pose-service
bolt: 028-model-pose-service
stage: model
status: complete
updated: 2026-07-18T04:10:25Z
---

# Static Model - Model Pose Service

## Bounded Context

**Model Pose Service** owns the `Model` identity concept for the multi-pose VTON generation intent: a named, mayorista-owned grouping of 1..3 pose-tagged photos of the same person. This context *extends* the existing `ModelPhoto` entity from the `001-media-service` bounded context (adds `model_id` FK + `pose` enum) rather than creating a parallel table — curated library photos stay in the same table with `model_id = null`. File validation and object storage remain owned by `001-media-service`; this context delegates to it.

**In scope**: `Model` aggregate, pose upload with fixed-enum + duplicate validation, pose listing.
**Out of scope**: curated model library, backfill migration (bolt 029), pose-aware submission (`002-pose-set-service`), UI, storage mechanics.

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| `Model` | `id` (UUID), `mayorista_id` (UUID, FK), `name` (str), `created_at` (timestamp) | `name` required, non-empty after trim, max 255 chars (else 400). `mayorista_id` always taken from the authenticated JWT session — never from the request body. Duplicate names for the same mayorista are allowed; `id` is the identity. May exist with zero poses, but is not usable in a submission until ≥1 pose exists. |
| `ModelPhoto` (extended) | `id` (UUID), `model_id` (UUID, FK → `Model`, **nullable**), `mayorista_id` (UUID, FK), `minio_key` (str), `pose` (`PoseType`, **nullable**), `is_curated` (bool), `uploaded_at` (timestamp) | `model_id = null` ⇔ curated library photo (or pre-backfill legacy row); such rows have `pose = null` and are invisible to this context's operations. When `model_id` is set, `pose` is required. At most one photo per `(model_id, pose)` — enforced by a DB unique constraint per ADR-010 pattern. `mayorista_id` must equal the owning `Model.mayorista_id`. Photo bytes must pass existing media validation (JPG/PNG, ≤10MB). |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| `PoseType` | `value`: one of `front`, `side`, `back` | Fixed enum — no arbitrary labels, no extension without a new intent. Defines deterministic display/listing order: `front` (0) < `side` (1) < `back` (2). |
| `PresignedUrl` | `url` (str), `expires_at` (timestamp) | TTL 15 minutes (existing media convention). Never logged (contains embedded credentials). Regenerated on every read — never persisted. |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| `Model` | `ModelPhoto` (pose photos, 0..3) | **Uniqueness of pose type**: no two member photos share the same `pose`. **Max 3 poses**: implied by `PoseType` cardinality + the uniqueness invariant. **Submission eligibility**: ≥1 pose required before the model can be used in a pose-set submission (eligibility is *evaluated* by `002-pose-set-service`; this aggregate only guarantees the count is observable). **Ownership**: all members share the root's `mayorista_id`. Deleting the root is out of scope for this bolt. |

*Note*: curated `ModelPhoto` rows (`is_curated = true`, `model_id = null`) live **outside** any `Model` aggregate — they are not members and are untouched by this bolt.

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `ModelCreated` | `create_model` succeeds | `model_id`, `mayorista_id`, `name`, `created_at` |
| `PosePhotoUploaded` | `upload_pose` succeeds (photo persisted + linked) | `model_photo_id`, `model_id`, `mayorista_id`, `pose`, `minio_key`, `uploaded_at` |
| `DuplicatePoseRejected` | `upload_pose` attempted with an already-used `pose` on the same model | `model_id`, `mayorista_id`, `pose` (observability only — the operation fails with 400) |

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| `ModelPoseService` | `create_model(mayorista_id, name) → Model`; `upload_pose(mayorista_id, model_id, pose, file) → ModelPhoto + PresignedUrl`; `list_poses(mayorista_id, model_id) → list[ModelPhoto + PresignedUrl]` | `ModelRepo`, `ModelPhotoRepo`, media upload/validation service (existing, from `001-media-service`), presigned-URL generator |

**Operation rules**:
1 - `upload_pose` first verifies the `Model` exists **and** belongs to `mayorista_id` — otherwise raise `ModelNotFound` (→ 404, never 403, to avoid leaking existence).
2 - `upload_pose` checks pose-type availability *before* touching storage (application-level fast-path per ADR-010); the DB unique constraint on `(model_id, pose)` is the authoritative guard under concurrency (`IntegrityError` → duplicate → 400).
3 - File type/size validation and MinIO write are **delegated** to the existing media upload path — this service never reimplements them.
4 - `list_poses` returns members ordered by `PoseType` order (`front`, `side`, `back`) with freshly generated presigned URLs; empty list is a valid result, not an error.

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| `ModelRepo` | `Model` | `create(model) → Model`; `get_by_id(model_id, mayorista_id) → Model \| None` (ownership-scoped) |
| `ModelPhotoRepo` | `ModelPhoto` | `create(model_photo) → ModelPhoto`; `list_by_model(model_id) → list[ModelPhoto]` (ordered `front, side, back`); `pose_exists(model_id, pose) → bool` (fast-path duplicate check) |

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Mayorista** | The authenticated wholesale customer who owns models, garments, and jobs. |
| **Model** | A named identity grouping 1..3 pose photos of the same person, owned by a mayorista. |
| **Pose / Pose Type** | The camera angle of a model photo. Fixed set: `front`, `side`, `back`. |
| **Pose Photo** | A `ModelPhoto` linked to a `Model` with a pose type. |
| **Curated ModelPhoto** | A platform-provided library photo (`is_curated = true`, `model_id = null`). Not owned, not backfilled, not listable via this context. |
| **Legacy ModelPhoto** | A mayorista-owned `ModelPhoto` created before this intent (`model_id = null`). Wrapped into an implicit single-pose `Model` by the bolt-029 backfill. |
| **Presigned URL** | Time-limited (15-min) MinIO URL granting read access to a photo. |
| **Mayorista namespace** | The per-mayorista MinIO key prefix under which all uploads are stored. |

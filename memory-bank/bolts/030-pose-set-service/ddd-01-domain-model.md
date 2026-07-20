---
unit: 002-pose-set-service
bolt: 030-pose-set-service
stage: model
status: complete
updated: 2026-07-18T06:47:24Z
---

# Static Model - Pose Set Service

## Bounded Context

**Pose Set Service** coordinates a mayorista's multi-pose VTON submission. It
owns the `PoseSet` identity and grouping metadata, while delegating job
creation, execution, retry, and item status transitions to the existing
`BatchJob`/`BatchItem` domain from intent 005.

The context receives a garment, a model, and a non-empty subset of that
model's pose photos. Each selected pose becomes one existing `BatchItem`.
Results are read back through the `PoseSet` grouping and the existing batch
state; no new inference or retry domain is introduced.

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| `PoseSet` | `id` (UUID), `mayorista_id`, `model_id`, `garment_id`, `batch_id` (unique), `created_at` | Owns the grouping identity for one submission. Exactly one `BatchJob` per PoseSet. `mayorista_id` must own the model and garment. Created atomically with the delegated batch. |
| `BatchJob` (existing) | Existing batch identity, status, counters, timestamps | PoseSet does not modify its lifecycle rules. `BatchJob.id` is the unique link target from `PoseSet`. |
| `BatchItem` (existing) | Existing item identity, `batch_id`, `garment_id`, `model_id`, status, result/error fields | One item per selected pose. `model_id` points to the selected `ModelPhoto.id` (the pose image used by VTON), not the parent Model identity. Item status is authoritative for per-pose results. |
| `ModelPhoto` (existing) | Existing pose photo with `model_id`, `pose`, `mayorista_id`, storage key | Every selected ID must belong to the requested parent Model and current mayorista. `pose` supplies the result's `pose_type`. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| `PoseSelection` | Ordered collection of `ModelPhoto.id` values | Must be non-empty; every ID must belong to the requested Model and mayorista; duplicate IDs are rejected with 400 rather than silently changing caller input. Maximum is the model's available pose count (currently 3). |
| `PoseSetStatus` | `pending`, `in-progress`, `complete`, `partial`, `failed` | Derived from the underlying `BatchJob` status and item outcomes; never independently persisted on PoseSet. |
| `PoseResult` | `pose_type`, `batch_item_id`, `media_id`, `image_url`, `status`, optional `error_message` | One result projection per selected BatchItem. `image_url` is present only when result media exists; errors mirror the BatchItem error. |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| `PoseSet` | One `BatchJob` reference; result projections over its `BatchItem`s | `batch_id` unique and non-null. Creation is atomic with BatchJob/BatchItems: no PoseSet without its batch and no batch without its PoseSet linkage when the operation succeeds. All records share `mayorista_id`. |
| `BatchJob` (owned by intent 005) | `BatchItem`s and existing VTON job links | PoseSet reads and delegates to this aggregate but does not duplicate or alter its domain rules. Its status is the source for grouped status derivation. |

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `PoseSetSubmitted` | PoseSet and delegated BatchJob/BatchItems commit successfully | `pose_set_id`, `batch_id`, `mayorista_id`, `model_id`, `garment_id`, `total_items` |
| `PoseSetSubmissionRejected` | Validation or delegated batch creation fails before commit | `mayorista_id`, `model_id`, `garment_id`, rejection reason; no persistent PoseSet or batch records remain |
| `PoseSetResultsViewed` | Grouped result projection is requested successfully | `pose_set_id`, `mayorista_id`, current derived status; observational only |

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| `PoseSetSubmissionService` | `submit_pose_set(mayorista_id, garment_id, model_id, cloth_type, pose_ids) → PoseSetSubmission` | Ownership-scoped ModelPhoto lookup, garment ownership validation, existing batch creation service, shared `AsyncSession` transaction |
| `PoseSetResultService` | `get_pose_set(mayorista_id, pose_set_id) → PoseSetResult` | Ownership-scoped PoseSet repository, existing BatchJob/BatchItem queries, ModelPhoto pose lookup, existing media URL generator |

**Submission rules**:
1 - Validate the garment and parent Model belong to the mayorista.
2 - Validate `pose_ids` is non-empty, duplicate-free, and an exact subset of
   the requested Model's pose photos.
3 - Build pairings using each selected `ModelPhoto.id` as the BatchItem's
   model input, then call the existing batch creation operation.
4 - Persist PoseSet in the same database transaction as the delegated batch;
   rollback all records if any step fails.
5 - Publish/enqueue work only through the existing post-commit batch flow.

**Result rules**:
1 - Fetch PoseSet ownership-scoped; missing and unowned records return the same
   not-found outcome.
2 - Derive set status from BatchJob and item states. A mixture of completed and
   failed/pending items is `partial`.
3 - Map each BatchItem's selected `model_id` back to ModelPhoto.pose.
4 - Include each item's status and error message; include media ID and a fresh
   presigned image URL when result media exists.

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| `PoseSetRepo` | `PoseSet` | `create`; `get_by_id_and_mayorista(pose_set_id, mayorista_id)`; `get_with_batch(pose_set_id, mayorista_id)` |
| `ModelPhotoRepo` | `ModelPhoto` | `list_by_ids_for_model(pose_ids, model_id, mayorista_id)`; return only owned, matching pose photos |
| Existing `BatchRepo` | `BatchJob`/`BatchItem` | Reuse existing atomic batch creation and grouped item/status queries; no duplicate implementation |
| Existing `MediaItemRepo` | Result media | Ownership-scoped result lookup and presigned URL generation via existing media service |

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **PoseSet** | The mayorista-visible grouping for one garment against selected poses of one Model. |
| **Selected pose** | A `ModelPhoto` row chosen by ID for a PoseSet submission. |
| **PoseSet submission** | The atomic operation that validates selection and creates the PoseSet plus delegated batch. |
| **BatchItem** | Existing one-pose execution item created by the batch domain; its `model_id` points to a ModelPhoto. |
| **Grouped result** | A PoseSet projection combining BatchJob status with one result entry per selected BatchItem. |
| **Partial** | A grouped state where items have mixed outcomes, such as some complete and one failed or pending. |

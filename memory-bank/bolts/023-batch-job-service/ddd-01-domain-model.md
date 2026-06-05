---
unit: 001-batch-job-service
bolt: 023-batch-job-service
stage: model
status: complete
created: 2026-06-04T00:00:00Z
---

# Static Model - Batch Job Service

## Bounded Context

**Batch VTON Generation** — Coordinates multi-item virtual try-on job submission, tracking, and lifecycle management for mayoristas. This context owns the `BatchJob` aggregate and orchestrates delegation to the existing `VtonJob` domain for individual inference execution.

**Boundary**: The batch context does not execute VTON inference. It creates, enqueues, and tracks batches. Inference execution remains in the `002-vton-job-service` bounded context.

## Domain Entities

- **BatchJob**: Aggregate root representing a named group of VTON pairings submitted by a mayorista. Properties: `id` (UUID), `mayorista_id` (UUID), `name` (string), `status` (BatchJobStatus), `total_items` (int), `completed_count` (int, default 0), `failed_count` (int, default 0), `created_at` (datetime), `completed_at` (datetime, nullable). Business rules: `total_items` must be 1–100; `completed_count + failed_count` cannot exceed `total_items`; status transitions are `pending → in-progress → complete|partial|failed`.

- **BatchItem**: Entity within the `BatchJob` aggregate representing a single garment+model pairing. Properties: `id` (UUID), `batch_id` (UUID FK), `garment_id` (UUID), `model_id` (UUID), `cloth_type` (ClothType), `vton_job_id` (UUID, nullable FK to VtonJob), `status` (BatchItemStatus), `error_message` (string, nullable), `result_media_id` (UUID, nullable), `created_at` (datetime), `completed_at` (datetime, nullable). Business rules: `garment_id` and `model_id` must belong to the batch's mayorista; `vton_job_id` is set during enqueue; status transitions are `pending → processing → complete|failed`.

## Value Objects

- **BatchJobStatus**: Immutable enumeration of batch lifecycle states. Values: `pending`, `in-progress`, `complete`, `partial`, `failed`. Constraints: only valid transitions allowed (`pending → in-progress`, `in-progress → complete|partial|failed`).

- **BatchItemStatus**: Immutable enumeration of item lifecycle states. Values: `pending`, `processing`, `complete`, `failed`. Constraints: only valid transitions allowed (`pending → processing`, `processing → complete|failed`).

- **ClothType**: Immutable enumeration of garment categories required by VTON provider. Values: `upper_body`, `lower_body`, `dress`. Constraints: must match provider's accepted cloth types.

- **BatchItemCap**: Value object enforcing the maximum batch size invariant. Value: `100`. Constraint: any batch creation exceeding this cap is rejected with a domain error.

## Aggregates

- **BatchJob Aggregate**: Root: `BatchJob`. Members: `BatchJob` (root), `BatchItem` (children, 1..100). Invariants:
  - All `BatchItem` records must belong to the same `mayorista_id` as the root.
  - `total_items` must equal the count of `BatchItem` children.
  - `completed_count` and `failed_count` must be accurate reflections of child statuses.
  - Batch size cannot exceed `BatchItemCap` (100).
  - Status transitions must follow the defined state machine.
  - Atomic creation: either all `BatchItem` records are created with the root, or none.

## Domain Events

- **BatchCreated**: Trigger: `BatchJob` aggregate is persisted with all `BatchItem` children. Payload: `{ batch_id, mayorista_id, name, total_items, created_at }`. Consumers: audit logging, analytics.

- **BatchSubmitted**: Trigger: all `BatchItem` records have been enqueued as `VtonJob` and `BatchJob.status` transitions to `in-progress`. Payload: `{ batch_id, mayorista_id, total_items, submitted_at }`. Consumers: notification service, frontend polling.

- **BatchItemCompleted**: Trigger: a `BatchItem`'s linked `VtonJob` completes successfully. Payload: `{ batch_id, item_id, vton_job_id, result_media_id }`. Consumers: media library auto-save (later bolt), batch counter update.

- **BatchItemFailed**: Trigger: a `BatchItem`'s linked `VtonJob` fails. Payload: `{ batch_id, item_id, vton_job_id, error_message }`. Consumers: batch counter update, partial failure detection.

- **BatchCompleted**: Trigger: all `BatchItem` statuses are terminal and `failed_count == 0`. Payload: `{ batch_id, mayorista_id, total_items, completed_at }`. Consumers: notification service, frontend.

- **BatchPartiallyFailed**: Trigger: all `BatchItem` statuses are terminal and `failed_count > 0` but `completed_count > 0`. Payload: `{ batch_id, mayorista_id, completed_count, failed_count, completed_at }`. Consumers: notification service, frontend.

## Domain Services

- **BatchSubmissionService**: Operations: `create_and_submit(mayorista_id, batch_name, pairings[]) → BatchJob`. Dependencies: `BatchJobRepo`, `VtonJobService` (existing), `UnitOfWork` (transaction management). Responsibility: validates pairings, creates `BatchJob` + `BatchItem` records atomically, enqueues each item as a `VtonJob`, updates batch status to `in-progress`, publishes `BatchSubmitted` event. Throws: `BatchSizeExceededError`, `EmptyBatchError`, `MayoristaOwnershipError`, `BatchSubmissionError`.

## Repository Interfaces

- **BatchJobRepo**: Entity: `BatchJob`. Methods:
  - `create(batch: BatchJob, items: list[BatchItem]) → BatchJob` — atomic creation of aggregate
  - `get_by_id(batch_id: UUID, mayorista_id: UUID) → BatchJob | None` — fetch with mayorista scoping
  - `list_by_mayorista(mayorista_id: UUID, page: int, page_size: int) → PaginatedResult[BatchJob]` — paginated history
  - `update_status(batch_id: UUID, status: BatchJobStatus) → None` — status transition
  - `update_counters(batch_id: UUID, completed_count: int, failed_count: int) → None` — counter updates
  - `save(batch: BatchJob) → None` — persist aggregate changes

- **BatchItemRepo**: Entity: `BatchItem`. Methods:
  - `create_many(items: list[BatchItem]) → None` — bulk creation within transaction
  - `get_by_id(item_id: UUID, batch_id: UUID) → BatchItem | None` — fetch within aggregate
  - `update_status(item_id: UUID, status: BatchItemStatus, **kwargs) → None` — status + metadata update
  - `list_by_batch(batch_id: UUID) → list[BatchItem]` — all items for a batch

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Batch** | A named collection of 1–100 VTON pairings submitted together by a mayorista |
| **BatchJob** | The aggregate root representing a batch submission and its lifecycle |
| **BatchItem** | A single garment+model+cloth_type pairing within a batch |
| **Pairing** | A tuple of `(garment_id, model_id, cloth_type)` that becomes a `BatchItem` |
| **Mayorista** | The wholesaler user who owns garments, models, and batches |
| **Mayorista Scoping** | Authorization rule: mayoristas can only access their own batches, garments, and models |
| **Atomic Submission** | All-or-nothing creation: either the entire batch is persisted and enqueued, or nothing is |
| **Partial Failure** | A batch state where some items completed successfully and others failed |
| **VtonJob** | An individual VTON inference job (owned by a different bounded context) |
| **BatchItemCap** | The maximum number of items allowed in a single batch (100) |

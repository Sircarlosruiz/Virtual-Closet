---
unit: 001-batch-job-service
bolt: 025-batch-job-service
stage: model
status: complete
created: 2026-06-04T00:00:00Z
---

# Static Model - Batch Job Service (Media Save, History)

## Bounded Context

**Batch VTON Generation — Media & History** — Extends the batch completion callback to persist result images to the media library with batch metadata. Provides a paginated batch history listing endpoint for mayoristas.

**Boundary**: Media save is triggered within the Celery completion callback (same flow as status updates). History listing is a read-only query on existing `BatchJob` records.

## Domain Entities

- **BatchJob** (extended for history): Aggregate root with computed status. History query properties: `id`, `name`, `status`, `total_items`, `completed_count`, `failed_count`, `created_at`, `completed_at`. Business rules: history queries are mayorista-scoped (`WHERE mayorista_id = :current_user`), ordered by `created_at DESC`, paginated.

- **BatchItem** (extended for media save): Entity with media save capability. Additional properties: `result_media_id` (UUID, nullable FK to media_items), `media_save_error` (boolean, default false). Business rules: media save is idempotent (check `result_media_id` before saving); media save failure sets `media_save_error = true` but does not change item status; `result_media_id` is set only on successful save.

## Value Objects

- **MediaSaveContext**: Immutable context for media library save. Properties: `batch_id`, `batch_name`, `garment_id`, `model_id`, `vton_job_id`, `result_minio_key`. Constraints: all fields required; used as metadata dict when creating media item.

- **BatchHistoryPage**: Paginated result for batch history. Properties: `items` (list[BatchJobSummary]), `total` (int), `page` (int), `page_size` (int). Constraints: `page >= 1`, `page_size <= 100`.

- **BatchJobSummary**: Read-only projection for history listing. Properties: `id`, `name`, `status`, `total_items`, `completed_count`, `failed_count`, `created_at`.

## Aggregates

- **BatchJob Aggregate** (extended for history): Root: `BatchJob`. Extended invariants:
  - **History isolation**: Mayoristas can only see their own batches in history queries
  - **Media save idempotency**: If `BatchItem.result_media_id` is already set, skip media save (prevents duplicate entries on duplicate callbacks)
  - **Graceful degradation**: Media save failure does not affect `BatchItem.status` or batch counters; only sets `media_save_error` flag

## Domain Events

- **BatchItemMediaSaved**: Trigger: Result image successfully saved to media library. Payload: `{ batch_id, item_id, media_item_id, batch_name, garment_id, model_id }`. Consumers: Audit logging, notification service.

- **BatchItemMediaSaveFailed**: Trigger: Media save fails after retries. Payload: `{ batch_id, item_id, error_message }`. Consumers: Audit logging, monitoring/alerting.

## Domain Services

- **BatchMediaSaveService**: Operations: `save_result_to_media(batch_id, item_id, result_minio_key) → MediaItem | None`. Dependencies: `BatchJobRepo`, `MediaLibraryService`. Responsibility: Looks up batch and item, constructs media metadata, calls media library save, updates `BatchItem.result_media_id`. Returns `None` on failure (graceful degradation). Throws: None (catches and logs all errors).

- **BatchHistoryService**: Operations: `list_batches(mayorista_id, page, page_size) → BatchHistoryPage`. Dependencies: `BatchJobRepo`. Responsibility: Queries mayorista's batches with pagination, returns summary projections.

## Repository Interfaces

- **BatchJobRepo** (extended for history):
  - `list_by_mayorista(mayorista_id, page, page_size) → tuple[list[BatchJob], int]` — Paginated history (already exists from bolt 023)
  - `get_by_id(mayorista_id, batch_id) → BatchJob | None` — Single batch fetch (already exists)

- **BatchItemRepo** (extended for media save):
  - `set_result_media(item_id, media_id) → None` — Set `result_media_id` on successful save
  - `set_media_save_error(item_id, error_message) → None` — Set `media_save_error` flag on failure
  - `get_with_batch(item_id) → tuple[BatchItem, BatchJob] | None` — Fetch item with parent batch for media save context

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Media Save** | Persisting a VTON result image to the media library with batch metadata |
| **Idempotency** | Guarantee that duplicate callbacks don't create duplicate media entries (checked via `result_media_id`) |
| **Graceful Degradation** | Media save failure doesn't fail the batch item; error is logged and flagged |
| **Batch History** | Paginated, mayorista-scoped list of all batches in reverse-chronological order |
| **Media Metadata** | Dict of contextual information (`batch_id`, `batch_name`, `garment_id`, `model_id`) attached to media items |

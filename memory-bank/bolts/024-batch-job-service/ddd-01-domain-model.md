---
unit: 001-batch-job-service
bolt: 024-batch-job-service
stage: model
status: complete
created: 2026-06-04T00:00:00Z
---

# Static Model - Batch Job Service (Status, Isolation, Retry)

## Bounded Context

**Batch VTON Generation — Feedback Loop** — Extends the batch domain with completion callbacks, failure isolation, and retry mechanics. This context owns the lifecycle transitions of `BatchItem` and `BatchJob` after initial submission, reacting to external `VtonJob` completion/failure events.

**Boundary**: Does not execute VTON inference. Reacts to `VtonJob` terminal states via Celery signals/callbacks. Retry creates new `VtonJob` records (delegates to existing VtonJob domain).

## Domain Entities

- **BatchJob** (extended): Aggregate root with computed status derived from child `BatchItem` states. Additional properties: `completed_count` (int), `failed_count` (int), `completed_at` (datetime, nullable). Business rules: status transitions are driven by child state changes — `pending → in-progress → complete|partial|failed`; counters are monotonic (increment-only except on retry); `completed_at` is set when all items reach terminal state.

- **BatchItem** (extended): Entity with status state machine and retry capability. Additional properties: `vton_job_id` (UUID, nullable), `error_message` (string, nullable), `result_media_id` (UUID, nullable), `retry_count` (int, default 0). Business rules: status transitions are append-only (`pending → processing → complete|failed`); only `failed` items can be retried; retry resets status to `pending` and creates new `VtonJob`.

- **RetryAttempt**: Value object representing a single retry of a failed `BatchItem`. Properties: `original_vton_job_id` (UUID), `new_vton_job_id` (UUID), `attempted_at` (datetime), `reason` (string). Constraints: can only be created for items with `status: failed`.

## Value Objects

- **BatchItemStatusTransition**: Immutable record of a status change. Properties: `from_status`, `to_status`, `trigger` (vton_complete|vton_fail|retry|manual), `timestamp`. Constraints: only valid transitions allowed per state machine.

- **BatchJobComputedStatus**: Immutable derived status based on child states. Values: `complete` (all items complete), `partial` (some complete, some failed), `failed` (all items failed), `in-progress` (at least one item processing/pending). Computed from: `completed_count`, `failed_count`, `total_items`.

- **IsolationBoundary**: Value object defining the failure isolation scope. Properties: `batch_id`, `affected_item_ids` (list[UUID]), `unaffected_item_ids` (list[UUID]). Invariant: failure of any item in `affected_item_ids` must not alter the state of items in `unaffected_item_ids`.

## Aggregates

- **BatchJob Aggregate** (extended): Root: `BatchJob`. Members: `BatchJob` (root), `BatchItem` (children). Extended invariants:
  - **Counter consistency**: `completed_count + failed_count <= total_items` (retry can decrement failed_count)
  - **Status derivation**: `BatchJob.status` is a pure function of child states — no direct status writes allowed
  - **Isolation**: Each `BatchItem` status transition is independent; failure of one item does not cascade to siblings
  - **Terminal detection**: When `completed_count + failed_count == total_items`, batch is terminal and `completed_at` is set
  - **Retry safety**: Retry on a `BatchItem` resets its status to `pending`, decrements `failed_count`, and transitions batch back to `in-progress` if it was terminal

## Domain Events

- **BatchItemStatusChanged**: Trigger: `BatchItem.status` transitions to any new state. Payload: `{ batch_id, item_id, from_status, to_status, trigger, timestamp }`. Consumers: BatchJob status recomputation, audit logging, frontend polling.

- **BatchItemCompleted**: Trigger: `BatchItem.status` transitions to `complete` (from `processing`). Payload: `{ batch_id, item_id, vton_job_id, result_media_id }`. Consumers: `BatchJob.completed_count` increment, media library save (later bolt).

- **BatchItemFailed**: Trigger: `BatchItem.status` transitions to `failed` (from `processing`). Payload: `{ batch_id, item_id, vton_job_id, error_message }`. Consumers: `BatchJob.failed_count` increment, isolation boundary enforcement.

- **BatchItemRetried**: Trigger: `POST /api/batches/{id}/items/{item_id}/retry` succeeds. Payload: `{ batch_id, item_id, old_vton_job_id, new_vton_job_id, retry_count }`. Consumers: `BatchJob.failed_count` decrement, batch status re-evaluation.

- **BatchStatusComputed**: Trigger: All `BatchItem` statuses are terminal (`completed_count + failed_count == total_items`). Payload: `{ batch_id, computed_status, completed_count, failed_count, total_items, completed_at }`. Consumers: Notification service, frontend, media library batch trigger.

- **BatchRecovered**: Trigger: Retry on a terminal batch transitions it back to `in-progress`. Payload: `{ batch_id, from_status, to_status: "in-progress" }`. Consumers: Frontend polling, notification service.

## Domain Services

- **BatchCompletionHandler**: Operations: `on_vton_job_complete(vton_job_id, result_minio_key) → None`, `on_vton_job_failed(vton_job_id, error_message) → None`. Dependencies: `BatchJobRepo`, `UnitOfWork`. Responsibility: Looks up `BatchItem` via `VtonJob.batch_item_id`, updates item status, increments counters, recomputes batch status, publishes domain events. Throws: `ItemNotFoundError`, `CounterUpdateError`.

- **BatchRetryService**: Operations: `retry_item(batch_id, item_id, mayorista_id) → BatchItem`. Dependencies: `BatchJobRepo`, `VtonJobService`, `UnitOfWork`. Responsibility: Validates item is `failed`, verifies mayorista ownership, creates new `VtonJob`, updates `BatchItem` (status → pending, new vton_job_id, increment retry_count), decrements `failed_count`, re-evaluates batch status. Throws: `ItemNotFailedError`, `MayoristaOwnershipError`, `RetryEnqueueError`.

## Repository Interfaces

- **BatchJobRepo** (extended):
  - `increment_completed_count(batch_id: UUID) → int` — Atomic `UPDATE batch_jobs SET completed_count = completed_count + 1 WHERE id = :batch_id RETURNING completed_count`
  - `increment_failed_count(batch_id: UUID) → int` — Atomic `UPDATE batch_jobs SET failed_count = failed_count + 1 WHERE id = :batch_id RETURNING failed_count`
  - `decrement_failed_count(batch_id: UUID) → int` — Atomic `UPDATE batch_jobs SET failed_count = GREATEST(failed_count - 1, 0) WHERE id = :batch_id RETURNING failed_count`
  - `compute_status(batch_id: UUID) → str` — Pure function: reads counters and total_items, returns computed status
  - `mark_completed(batch_id: UUID) → None` — Sets `completed_at = NOW()` when batch reaches terminal state

- **BatchItemRepo** (extended):
  - `update_status_and_vton_job(item_id: UUID, status: str, vton_job_id: UUID | None, error_message: str | None) → BatchItem` — Atomic status update with metadata
  - `get_by_vton_job_id(vton_job_id: UUID) → BatchItem | None` — Lookup item via linked VtonJob (for callback)
  - `reset_for_retry(item_id: UUID, new_vton_job_id: UUID) → BatchItem` — Reset status to pending, set new vton_job_id, increment retry_count

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Completion Callback** | Celery signal or handler invoked when a `VtonJob` reaches a terminal state |
| **Counter Update** | Atomic increment/decrement of `completed_count` or `failed_count` using SQL `F()` expressions |
| **Isolation** | Guarantee that failure of one `BatchItem` does not affect processing of sibling items |
| **Computed Status** | `BatchJob.status` derived from child states, not directly written |
| **Terminal State** | All items have reached `complete` or `failed`; no further status changes expected |
| **Retry** | Manual re-enqueue of a failed `BatchItem` as a new `VtonJob` |
| **Recovery** | Transition of a terminal `BatchJob` back to `in-progress` after successful retry |
| **Lost Update** | Race condition where concurrent counter increments overwrite each other; prevented by `F()` expressions |

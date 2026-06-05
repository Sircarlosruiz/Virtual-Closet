---
intent: 005-batch-vton-generation
phase: inception
status: draft
created: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
---

# Requirements: Batch VTON Generation

## Intent Overview

A mayorista selects multiple garment + model combinations via a UI and submits them as a single named batch job. Each pairing is enqueued as an individual VTON job using the existing Celery/RabbitMQ pipeline. The mayorista monitors overall batch progress (total / completed / failed counts) and per-item status. Successful items are saved automatically to the media library. Failed items are flagged with an error reason and can be individually retried from within the batch view. Batches range from 10 to 100 items.

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Mayoristas can submit multiple VTON jobs in one action | First successful batch of ≥10 items submitted within 5 minutes of feature availability | Must |
| Partial failures don't block the whole batch | Successful items reach media library even if some jobs fail | Must |
| Mayoristas know exactly what's happening per item | Per-item status visible (pending / processing / done / failed) in real time | Must |
| Failed items can be recovered without resubmitting the whole batch | Retry failed items individually from batch detail view | Must |
| Batch results are usable immediately | Completed items appear in media library tagged with batch name | Must |

---

## Functional Requirements

### FR-1: Batch Creation UI
- **Description**: Mayorista opens a "New Batch" flow from the dashboard. They select garments from their media library and pair each with a model photo and a cloth type. Up to 100 pairings per batch. The batch can be given an optional name.
- **Acceptance Criteria**: UI allows selecting 10–100 garment+model+cloth_type pairings; optional batch name field; "Submit Batch" button disabled until at least 1 pairing is added; pairing count shown in real time.
- **Priority**: Must

### FR-2: Batch Submission
- **Description**: On submit, the backend creates a `BatchJob` record and enqueues each pairing as an individual VTON `Job` linked to the batch. Returns `batch_id` immediately.
- **Acceptance Criteria**: `POST /api/batches` responds within 500ms regardless of batch size; all individual jobs are enqueued atomically; response includes `{ batch_id, total_items, status: "pending" }`.
- **Priority**: Must

### FR-3: Batch Progress View
- **Description**: Mayorista can view a batch detail page showing overall progress (e.g., "14/20 completed, 2 failed, 4 in progress") and a per-item list with individual statuses.
- **Acceptance Criteria**: Batch detail page auto-refreshes or uses polling; overall counters reflect real-time state; per-item row shows garment thumbnail, model thumbnail, cloth type, status, and error message if failed.
- **Priority**: Must

### FR-4: Partial Failure Isolation
- **Description**: A failed individual job does not affect other jobs in the batch. The batch status reflects mixed results (e.g., `partial`). Successful items proceed to media library regardless of failures.
- **Acceptance Criteria**: A failed job sets that item's status to `failed` with an error reason; the batch's `completed_count` increments for each success independently; batch status is `complete` when all jobs reach a terminal state (success or failure).
- **Priority**: Must

### FR-5: Retry Failed Items
- **Description**: From the batch detail view, mayorista can retry individual failed items. Retry re-enqueues the same garment+model+cloth_type pairing as a new VTON job linked to the same batch.
- **Acceptance Criteria**: "Retry" button visible on each failed item row; clicking it re-enqueues the job and resets that item's status to `pending`; retried items count toward the same batch totals.
- **Priority**: Must

### FR-6: Automatic Media Library Save
- **Description**: When a batch item's VTON job completes successfully, the result image is automatically saved to the mayorista's media library. The media item is tagged with the batch name/ID for traceability.
- **Acceptance Criteria**: Completed item appears in media library within 5 seconds of job completion; media item metadata includes `batch_id` and `batch_name`; no manual action required from mayorista.
- **Priority**: Must

### FR-7: Batch History
- **Description**: Mayorista can view a list of all their past and active batches with summary status (name, date, total items, completed, failed).
- **Acceptance Criteria**: `/tryoff/batches` or dashboard widget lists batches in reverse-chronological order; each row shows name, created_at, total/completed/failed counts, and a link to the batch detail view.
- **Priority**: Should

---

## Non-Functional Requirements

### Performance
| Requirement | Metric | Target |
|-------------|--------|--------|
| Batch submission API | p95 response time | < 500ms (enqueue only, not processing) |
| Batch detail page load | p95 response time | < 300ms |
| Per-item status refresh | Polling interval | Every 3s on active batch |

### Scalability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Batch size | Items per batch | 10–100 |
| Concurrent mayoristas | Simultaneous active batches | Handled by existing Celery worker pool |

### Reliability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Individual job isolation | Failure blast radius | 1 job failure affects only that item |
| Auto-retry on transient failure | Retries before permanent failure | 3 (inherited from existing VTON job service) |
| Batch record persistence | Data loss on worker crash | Zero — batch and job records persisted in DB before enqueue |

### Security
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Authorization | Per-mayorista scoping | Mayorista can only view/manage their own batches |

---

## Constraints

### Technical Constraints

**Project-wide standards**: Loaded from memory-bank standards by Construction Agent.

**Intent-specific constraints**:
- Reuses existing Celery/RabbitMQ queue from `001-vton-generation-pipeline`; no new queue infrastructure required
- Individual VTON job logic (IDM-VTON inference, media save) must not be duplicated — batch jobs delegate to the existing job service
- Batch size hard cap: 100 items (enforced at API level)

### Business Constraints
- No CSV upload — UI only for this intent

---

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| Existing Celery worker pool can absorb 100-job spikes without tuning | Batch submission causes queue backup for other mayoristas | Add concurrency limits per mayorista if contention observed |
| Mayoristas have sufficient garments in media library to form batches | Feature unused if media library is sparse | No mitigation needed — TryOff extraction (004) feeds the library |
| Per-item polling every 3s is acceptable UX for batch status | Mayorista expects faster real-time updates | Can switch to WebSocket push in a future intent |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should batch submission be rate-limited per mayorista (e.g., 1 active batch at a time)? | Carlos | 2026-06-11 | Pending |

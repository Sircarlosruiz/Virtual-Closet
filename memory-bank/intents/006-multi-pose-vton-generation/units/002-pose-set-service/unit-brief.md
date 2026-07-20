---
unit: 002-pose-set-service
intent: 006-multi-pose-vton-generation
phase: inception
status: complete
unit_type: backend
default_bolt_type: ddd-construction-bolt
created: 2026-07-17T00:00:00.000Z
updated: 2026-07-17T00:00:00.000Z
---

# Unit Brief: pose-set-service

## Purpose

Backend domain that coordinates multi-pose generation submissions. Accepts a garment + model + selected pose ids, expands the request into the existing `BatchJob`/`BatchItem` pipeline (one item per selected pose), atomically registers a `PoseSet` linking the batch to the model and garment, and exposes grouped result retrieval.

## Scope

### In Scope
- `PoseSet` aggregate (Django model), 1:1 with a `BatchJob`
- `POST /api/pose-sets` — validate selected poses (non-empty subset of the model's poses), atomically create `PoseSet` + delegate to existing batch creation (`001-batch-job-service`) for `BatchJob`/`BatchItem` creation, one item per selected pose
- `GET /api/pose-sets/{pose_set_id}` — return grouped status/results, derived from the underlying `BatchJob`/`BatchItem` state
- Mayorista-scoped authorization on all endpoints

### Out of Scope
- `BatchJob`/`BatchItem` domain logic itself (reused unchanged from `001-batch-job-service`, intent `005-batch-vton-generation`)
- Individual VTON job execution (unchanged, `002-vton-job-service`, intent `001`)
- Per-item retry logic (reuses existing `POST /api/batches/{id}/items/{item_id}/retry` from `005`; no new retry endpoint)
- Model/pose CRUD (handled by `001-model-pose-service`)
- Frontend UI (handled by `003-multi-pose-vton-generation-ui`)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-3 | Pose-aware submission API accepting a non-empty subset of a model's poses | Must |
| FR-4 | Expand submission into `BatchJob`/`BatchItem`s, one per selected pose | Must |
| FR-5 | Atomically register `PoseSet` alongside the `BatchJob` | Must |
| FR-6 | Grouped result retrieval with per-pose status (API) | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `PoseSet` | Links a garment+model multi-pose submission to its `BatchJob` | `id`, `mayorista_id`, `model_id`, `garment_id`, `batch_id` (unique, 1:1), `created_at` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `submit_pose_set` | Validates `pose_ids` is a non-empty subset of the model's poses; builds pairings `(garment_id, model_id_of_pose, cloth_type)` per selected pose; calls existing `create_batch` (from `001-batch-job-service`); persists `PoseSet` in the same transaction | `mayorista_id`, `garment_id`, `model_id`, `cloth_type`, `pose_ids[]` | `{ pose_set_id, batch_id, total_items }` |
| `get_pose_set` | Fetches `PoseSet`, joins with `BatchJob`/`BatchItem` state, maps each item back to its pose type | `pose_set_id`, `mayorista_id` | `{ pose_set_id, garment_id, model_id, status, items: [{pose_type, batch_item_id, media_id, image_url, status}] }` |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 2 |
| Must Have | 2 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-submit-pose-set | Submit Pose-Aware Generation and Register PoseSet | Must | Planned |
| 002-view-pose-set-results | View Grouped Pose Set Results | Must | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `001-model-pose-service` (this intent) | Reads a model's poses to validate `pose_ids` and resolve pose-to-photo mapping |
| `001-batch-job-service` (intent `005-batch-vton-generation`) | Reused unchanged for `BatchJob`/`BatchItem` creation, status, and per-item retry |

### Depended By

| Unit | Reason |
|------|--------|
| `003-multi-pose-vton-generation-ui` | Consumes submission and result-retrieval endpoints |

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| PostgreSQL | `PoseSet` metadata persistence | Low |

---

## Technical Context

### Suggested Technology
- New `PoseSet` Django model in a new or existing `pose_sets` app
- Direct internal call into `001-batch-job-service`'s `create_batch` operation (same transaction via `transaction.atomic`)
- DRF serializer/ViewSet for `POST /api/pose-sets` and `GET /api/pose-sets/{id}`

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| `001-batch-job-service` `create_batch` | Internal service call | Python function call (same transaction) |
| `001-model-pose-service` pose lookup | Internal service call or REST | Python function call preferred (same backend) |

### Data Storage

| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| `PoseSet` records | PostgreSQL | Low (1 per multi-pose submission) | Permanent |

---

## Constraints

- `PoseSet` creation must be atomic with `BatchJob`/`BatchItem` creation — no orphaned `PoseSet`
- `pose_ids` must be non-empty and must all belong to the specified `model_id` and the requesting mayorista
- Must not modify `001-batch-job-service` domain logic — call its existing creation path as-is
- No new retry endpoint — pose-level retry reuses `005`'s existing per-item retry

---

## Success Criteria

### Functional
- [ ] Submitting with 1–3 selected poses creates a `BatchJob` with matching `total_items` and a linked `PoseSet`
- [ ] Empty `pose_ids` is rejected with 400
- [ ] `GET /api/pose-sets/{id}` returns correct per-pose status reflecting underlying `BatchItem` state
- [ ] A `PoseSet` is never created without its `BatchJob`, and vice versa

### Non-Functional
- [ ] Submission API responds < 500ms p95 (enqueue only, mirrors `005` batch NFR)
- [ ] Mayorista cannot access another mayorista's `PoseSet` records

### Quality
- [ ] Code coverage > 80%
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 030-pose-set-service | ddd-construction-bolt | 001, 002 | `PoseSet` domain model + atomic submission + grouped retrieval |

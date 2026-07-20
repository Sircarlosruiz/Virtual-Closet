---
intent: 006-multi-pose-vton-generation
phase: inception
status: complete
created: 2026-07-17T00:00:00.000Z
updated: 2026-07-17T00:00:00.000Z
---

# Requirements: Multi-Pose VTON Generation

## Intent Overview

Extends model management so a mayorista can attach a small fixed set of pose photos (e.g., front/side/back, ~3-5) to a single model identity, instead of one photo per model. When submitting a garment for VTON generation against a multi-pose model, the mayorista can request generation across all of that model's poses in one action. Generation is executed by expanding into the existing `BatchJob` pipeline (`005-batch-vton-generation`) — one batch item per pose — rather than a new job-processing path. The resulting per-pose outputs are linked together as a single "pose set" in the media library/catalog UI, so a garment's multi-angle views can be viewed and used as a group.

Curated library models remain single-pose for now; multi-pose is scoped to a mayorista's own uploaded models only.

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Mayoristas can show garments from multiple angles without manual re-submission | One "generate all poses" action produces front/side/back outputs for a garment+model | Must |
| Multi-pose generation reuses existing batch infrastructure | No new job-execution path; multi-pose submissions create standard `BatchJob` + `Job` records | Must |
| Pose outputs are usable as a set, not scattered items | Mayorista can view/select all poses of one garment+model generation together in the media library | Must |
| Pose photo management is simple and bounded | Mayorista can add/remove pose photos per model up to the fixed cap without confusion | Should |

---

## Functional Requirements

### FR-1: Model Entity with Pose Photo Upload
- **Description**: A mayorista creates a `Model` (a named identity) and uploads pose photos to it. Each pose photo is tagged with a pose type drawn from a fixed enumeration (`front`, `side`, `back`). This replaces the flat `ModelPhoto`-as-model concept in `001-vton-generation-pipeline` with `Model` (1) → `ModelPhoto` (1..N poses).
- **Acceptance Criteria**: `POST /api/models` creates `{id, mayorista_id, name, created_at}`; `POST /api/models/{model_id}/poses` uploads a photo tagged with one pose type from `{front, side, back}`; a given pose type can be used at most once per `Model` (duplicate pose type on same model rejected 400); a `Model` must have at least 1 pose; uploads follow existing file validation (JPG/PNG, max 10MB) from `001-vton-generation-pipeline` FR-1.
- **Priority**: Must
- **Related Stories**: TBD

### FR-2: List Model Poses
- **Description**: Mayorista can retrieve all poses registered for one of their models.
- **Acceptance Criteria**: `GET /api/models/{model_id}/poses` returns each `ModelPhoto` with its `pose` type and a pre-signed access URL (15-min TTL, per existing convention); only the owning mayorista can list; 404 if model not found or not owned.
- **Priority**: Must
- **Related Stories**: TBD

### FR-3: Pose-Aware Garment Submission with Deselection
- **Description**: When submitting a garment for VTON generation against a multi-pose `Model`, the mayorista sees all of that model's poses and can deselect specific poses before submitting. At least one pose must remain selected.
- **Acceptance Criteria**: Submission accepts `{garment_id, model_id, cloth_type, pose_ids[]}` where `pose_ids` is a non-empty subset of the model's `ModelPhoto` ids; empty `pose_ids` is rejected with 400; a model with exactly 1 pose behaves identically to today's single-pairing submission.
- **Priority**: Must
- **Related Stories**: TBD

### FR-4: Multi-Pose Batch Expansion
- **Description**: Submitting a pose-aware garment request expands into the existing `BatchJob`/`BatchItem` pipeline (`005-batch-vton-generation`) — one `BatchItem` per selected pose, sharing the same `garment_id` and `cloth_type`. No new job-execution mechanism is introduced.
- **Acceptance Criteria**: The submission creates a `BatchJob` with `total_items` equal to the number of selected poses; each resulting `BatchItem.model_id` references the specific pose's `ModelPhoto` id; existing `BatchJob` invariants (size 1–100, atomic creation, mayorista scoping) apply unchanged; response includes `batch_id`.
- **Priority**: Must
- **Related Stories**: TBD

### FR-5: PoseSet Registration
- **Description**: A new `PoseSet` aggregate is created atomically with the `BatchJob` at submission time, recording that a given garment was generated across a given model's (selected) poses.
- **Acceptance Criteria**: `PoseSet{id, mayorista_id, model_id, garment_id, batch_id, created_at}` is persisted in the same transaction as the `BatchJob`/`BatchItem`s (all-or-nothing, matching the `BatchJob` atomicity invariant); `batch_id` is unique to one `PoseSet` (1:1); `PoseSet` is queryable by id, scoped to the owning mayorista.
- **Priority**: Must
- **Related Stories**: TBD

### FR-6: Pose Set Result Retrieval
- **Description**: The mayorista can view a `PoseSet`'s generation results as one linked group, showing per-pose status and output image once available.
- **Acceptance Criteria**: `GET /api/pose-sets/{pose_set_id}` returns `{pose_set_id, garment_id, model_id, status, items: [{pose_type, batch_item_id, media_id, image_url, status}]}`; `status` is derived from the underlying `BatchJob` status (`pending/in-progress/complete/partial/failed`); partial completion (some poses done, others pending/failed) is represented per-item, consistent with existing batch partial-failure semantics; a failed pose within the set can be retried individually using the existing per-item batch retry (`005-batch-vton-generation` FR-5) with no new retry mechanism.
- **Priority**: Must
- **Related Stories**: TBD

### FR-7: Backward Compatibility for Single-Pose Usage
- **Description**: Mayoristas who never add extra poses continue to use today's flows unchanged.
- **Acceptance Criteria**: Existing pairing-based `POST /api/batches` (`005-batch-vton-generation` FR-2) and the single VTON job submission (`001-vton-generation-pipeline`) continue to work without requiring a `Model`/`PoseSet`; pre-existing `ModelPhoto` rows created before this intent are backfilled into an implicit single-pose `Model` wrapper (one `Model` per legacy `ModelPhoto`, pose type defaulted to `front`) so no mayorista-facing data is lost.
- **Priority**: Must
- **Related Stories**: TBD

---

## Non-Functional Requirements

### Performance
| Requirement | Metric | Target |
|-------------|--------|--------|
| Pose-set submission latency | API response time, regardless of pose count (max 3) | < 500ms (matches `005` batch submission NFR) |

### Reliability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Atomic PoseSet + BatchJob creation | Failure mode | Either both are persisted and enqueued, or neither is (no orphaned `PoseSet` without a `BatchJob`) |

### Security
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Mayorista scoping | Same authorization model as existing units | `Model`, `ModelPhoto` (poses), and `PoseSet` are only readable/writable by the owning mayorista |

---

## Constraints

### Technical Constraints

**Project-wide standards**: Required standards will be loaded from memory-bank standards folder by Construction Agent

**Intent-specific constraints**:
- Pose type is a fixed enumeration (`front`, `side`, `back`); a `Model` cannot have more poses than enum values, and cannot repeat a pose type.
- Multi-pose generation must build on the existing `BatchJob`/`BatchItem` pipeline from `005-batch-vton-generation` — no parallel job-execution mechanism.
- Curated model library is out of scope; only mayorista-uploaded models support multiple poses.
- Pre-existing `ModelPhoto` rows must be backfilled into implicit single-pose `Model` wrappers — no data loss, no forced re-upload.

### Business Constraints
- None identified beyond the above.

---

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| Pose enum finalized as `{front, side, back}` for MVP | Too few angles for some buyer use cases | Enum is designed to be extensible in a future intent |
| Existing batch retry-per-item (FR-5 of `005`) is sufficient for retrying a single failed pose within a `PoseSet` | Might need pose-set-aware retry/regeneration semantics later | Reuse as-is for MVP; revisit if mayorista feedback demands set-aware retry |
| Legacy `ModelPhoto` backfill defaults every pre-existing photo to pose type `front` | A mayorista's legacy model was actually a side/back shot, mislabeled after backfill | Acceptable for MVP since legacy models remain single-pose and functionally unaffected; label is cosmetic until they add more poses |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should the catalog UI display pose sets as a single item with angle switcher, or as separate catalog items? | Mayorista/Product | TBD | Pending — deferred to a future catalog-facing intent; out of scope for this intent's units |
| Should the pose enum grow beyond 3 values (e.g., add `three_quarter`) in a follow-up? | Product | TBD | Pending — not blocking MVP |

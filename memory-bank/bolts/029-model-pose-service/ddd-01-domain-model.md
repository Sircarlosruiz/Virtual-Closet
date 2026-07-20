---
unit: 001-model-pose-service
bolt: 029-model-pose-service
stage: model
status: complete
updated: 2026-07-18T05:12:30Z
---

# Static Model - Model Pose Service (Legacy Backfill)

## Bounded Context

**Model Pose Service — Backfill Operation.** A one-time, idempotent data migration that wraps every pre-existing (legacy) mayorista-owned `ModelPhoto` row in its own single-pose `Model`, so that after intent 006 every non-curated photo has a `Model` parent. This bolt changes **data only** — no new entities, no API surface. It operates entirely within the schema and invariants delivered by bolt 028 (ADR-012).

**In scope**: legacy `ModelPhoto` rows (`is_curated = false AND model_id IS NULL AND mayorista_id IS NOT NULL`).
**Out of scope**: curated rows, API changes, manual merging of wrapper Models, pose inference (every legacy photo becomes `front` — angles cannot be inferred retroactively).

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| `Model` (backfill-created wrapper) | `id` (new UUID), `mayorista_id` (copied from the photo), `name` (derived, see below), `created_at` (now) | Exactly one wrapper per legacy photo — **1:1, never grouped** (grouping is not inferable, story 004 edge case). `mayorista_id` must equal the photo's `mayorista_id` (ownership invariant from 028). `name` is derived deterministically from the photo's `label` (e.g., `"{label}"` truncated to 255) — names are not unique keys (028 domain model), so collisions are harmless. |
| `ModelPhoto` (legacy row) | *(existing)* all columns; `model_id = NULL`, `pose = NULL`, `is_curated = false`, `mayorista_id` set | After backfill: `model_id` = wrapper's id **and** `pose = 'front'`, set in the **same atomic UPDATE** — the coupling CHECK `(model_id IS NULL) = (pose IS NULL)` (ADR-012) forbids setting one without the other. Row is otherwise untouched (`minio_key`, `label`, `is_curated`, content metadata preserved — lossless). |
| `ModelPhoto` (curated row) | `is_curated = true`, `model_id = NULL` | **Excluded entirely** — never selected, never modified. Also excluded: any non-curated row already having `model_id` (idempotency filter) and rows with `mayorista_id IS NULL` (orphaned uploads have no owner to wrap; see Risks in technical design). |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| `BackfillSelection` | filter predicate | `is_curated = false AND model_id IS NULL AND mayorista_id IS NOT NULL` — this exact predicate is both the work set and the idempotency key: a row matching it means "not yet backfilled". |
| `BackfillBatch` | `size` (row count per transaction) | Per-batch transactions (story 004 tech note) — no single giant lock on `model_photos`; a failed batch does not roll back completed batches. |
| `PoseType` | *(from 028)* | Backfill always assigns `front` — the canonical default; `side`/`back` are never assigned retroactively. |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| `Model` (wrapper) | exactly 1 `ModelPhoto` | Post-migration global invariants: (a) **parity** — count of non-curated, mayorista-owned photos with `model_id IS NULL` = 0; (b) **single pose** — every wrapper has exactly 1 member with `pose = 'front'`; (c) **uniqueness** — `(model_id, pose)` unique holds trivially (1 pose per wrapper); (d) **curated untouched** — no curated row has `model_id` set. |

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `LegacyModelPhotoBackfilled` | One legacy row linked to its new wrapper | `model_photo_id`, `model_id`, `mayorista_id` (migration log line per row) |
| `BackfillCompleted` | Migration pass finishes | `rows_backfilled`, `batches`, `duration` (summary log) |

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| `LegacyModelBackfillService` | `backfill_legacy_models(batch_size) → BackfillReport` | `ModelRepo` (insert wrappers), `ModelPhotoRepo` (select legacy rows by `BackfillSelection`, atomic link update) |

**Operation rules**:
1 - **Idempotent**: re-running selects only rows still matching `BackfillSelection`; already-linked rows are never re-selected → no duplicate wrappers (story AC #2).
2 - **Atomic per row**: wrapper INSERT + photo UPDATE commit in the same batch transaction; the coupling CHECK can never observe a half-linked row.
3 - **Batched**: process `batch_size` rows per transaction to keep lock scope small; loop until the selection is empty.
4 - **Lossless**: the migration never deletes rows, never rewrites `minio_key`/`label`, never touches curated rows.
5 - **Safe on empty**: selection empty on first pass → immediate no-op success (story edge case).

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| `ModelRepo` | `Model` | *(existing from 028)* `create` — reused per wrapper (within batch session) |
| `ModelPhotoRepo` | `ModelPhoto` | `list_legacy_unlinked(limit) → list[ModelPhoto]` (the `BackfillSelection` predicate, oldest-first); `link_to_model(photo_id, model_id, pose='front')` (single atomic UPDATE) |

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Legacy ModelPhoto** | A mayorista-owned, non-curated `ModelPhoto` created before intent 006 (`model_id = NULL`). |
| **Wrapper Model** | A `Model` created by the backfill solely to give one legacy photo a parent; has exactly one `front` pose. |
| **Backfill** | The one-time, re-runnable migration that creates wrapper Models and links legacy photos. |
| **Idempotent re-run** | A second execution that selects zero rows and changes nothing. |
| **Parity** | Post-condition: zero non-curated, mayorista-owned photos remain without `model_id`. |

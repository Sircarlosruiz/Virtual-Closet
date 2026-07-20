---
id: 004-backfill-legacy-models
unit: 001-model-pose-service
intent: 006-multi-pose-vton-generation
status: complete
priority: must
created: 2026-07-17T00:00:00.000Z
assigned_bolt: 029-model-pose-service
implemented: true
---

# Story: 004-backfill-legacy-models

## User Story

**As a** mayorista who uploaded model photos before this feature existed
**I want** my existing model photos to keep working exactly as before
**So that** I don't lose access to any model or have to re-upload anything

## Acceptance Criteria

- [ ] **Given** a `ModelPhoto` row exists with `is_curated=false` and no `model_id` (pre-intent data), **When** the backfill migration runs, **Then** a new `Model` is created for that photo's `mayorista_id` and the `ModelPhoto` is linked to it with `pose=front`
- [ ] **Given** the backfill has already run for a `ModelPhoto`, **When** it is run again, **Then** it is a no-op for that row (idempotent — skips rows that already have a `model_id`)
- [ ] **Given** a `ModelPhoto` row has `is_curated=true`, **When** the backfill runs, **Then** it is skipped entirely (`model_id` stays null)
- [ ] **Given** the backfill completes, **When** counting rows, **Then** every non-curated `ModelPhoto` has a non-null `model_id` and every backfilled `Model` has exactly 1 pose

## Technical Notes

- Implement as a Django data migration (not a management command), run once as part of deploying this intent
- Wrap in `transaction.atomic()` per-batch to avoid a single giant lock on large tables

## Dependencies

### Requires
- 001-create-model, 002-upload-pose-photo (schema for `Model` and extended `ModelPhoto` must exist)

### Enables
- FR-7 backward compatibility guarantee for the whole intent

## Edge Cases

| Scenario | Expected Behavior |
|----------|--------------------|
| Mayorista has multiple legacy `ModelPhoto` rows | Each gets its own separate `Model` (1:1), not grouped together — grouping legacy photos is not inferable and out of scope |
| Migration run on empty table | No-op, completes immediately |

## Out of Scope

- Letting a mayorista manually merge multiple legacy `Model` wrappers into one multi-pose `Model` (not required by any FR; could be a future enhancement)

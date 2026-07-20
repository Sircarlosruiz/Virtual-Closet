---
unit: 001-model-pose-service
bolt: 029-model-pose-service
stage: design
status: complete
updated: 2026-07-18T05:12:30Z
---

# Technical Design - Legacy ModelPhoto Backfill

## Architecture Pattern

**Alembic data migration** (new revision chained on 028's `f1e2d3c4b5a6`), executed automatically by `alembic upgrade head` at deploy time. The story's "Django data migration (not a management command)" maps to the project's actual stack: an Alembic revision is the automatic, deploy-integrated, non-manual equivalent (same mapping established in bolt 028's technical design).

*Rationale*: (a) runs exactly once per environment via Alembic version tracking, yet remains **operationally idempotent** via its selection predicate (a failed run leaves no partial state for completed batches, and a re-run — e.g., via a repeat migration or manual re-execute — selects only still-unlinked rows); (b) no runtime code, no API surface; (c) reversible deploy story remains with 028's schema migration.

## Layer Structure

```text
┌─────────────────────────────────────────────┐
│  Deploy        alembic upgrade head         │  automatic at deploy
├─────────────────────────────────────────────┤
│  Migration     alembic/versions/b7c8d9e0f1a2│  batch loop, per-batch commits
├─────────────────────────────────────────────┤
│  Data          models / model_photos        │  INSERT wrappers + atomic link UPDATE
└─────────────────────────────────────────────┘
```

## Migration Design

**Revision**: `b7c8d9e0f1a2_backfill_legacy_model_photos.py` — `down_revision = "f1e2d3c4b5a6"` (data migration; no schema changes).

**Batch size**: `500` rows per bounded read (module constant). The current
Alembic `env.py` owns one migration transaction around `context.run_migrations()`;
the revision therefore does not call `commit()` internally. This preserves
Alembic's transaction lifecycle while preventing an unbounded result set. A
future migration-runner change can move the batch loop to independently
committed transactions if live-table lock duration requires it.

**upgrade() algorithm**:

1. Use the transaction supplied by Alembic's migration context and read at most 500 rows per iteration.
2. Loop:
   a. `SELECT id, mayorista_id, label FROM model_photos WHERE is_curated = false AND model_id IS NULL AND mayorista_id IS NOT NULL ORDER BY uploaded_at LIMIT 500` (oldest-first, deterministic).
   b. If zero rows → break (covers empty-table no-op and final pass).
   c. For each row: `INSERT INTO models (id, mayorista_id, name, created_at) VALUES (gen_random_uuid(), :mayorista_id, :name, now()) RETURNING id` where `name = label[:255]` (label is `NOT NULL`, ≤255 chars; duplicate names are allowed per 028's domain model).
   d. `UPDATE model_photos SET model_id = :model_id, pose = 'front' WHERE id = :photo_id AND model_id IS NULL` — single atomic statement satisfying the coupling CHECK; the redundant `model_id IS NULL` guard makes the UPDATE safe against concurrent linking.
   e. Log `LegacyModelPhotoBackfilled` per row (photo_id, model_id) at debug level and a per-batch count at info level.
3. Log `BackfillCompleted` summary: `rows_backfilled`, `batches`, and `rows_skipped_orphaned` (count of `is_curated = false AND model_id IS NULL AND mayorista_id IS NULL` — orphaned rows are intentionally not wrapped; they have no owner).

**Idempotency**: the selection predicate *is* the idempotency mechanism — any row already linked (by a previous batch, a previous run, or live traffic via 028's API) no longer matches, so re-execution creates zero duplicate wrappers. Story AC #2 satisfied structurally.

**Deploy-window race**: while the migration runs, 028's API can only create rows that already have `model_id` (pose uploads) — they never match the selection. The legacy single-photo endpoint (`POST /api/media/models`) can still create `model_id = NULL` rows during the window; those are picked up by re-running the backfill (documented operational follow-up, story's "safely re-runnable" requirement).

**downgrade()**: no-op (documented in the file). Data migrations that create parent rows are not safely reversible — a wrapper `Model` is indistinguishable from a user-created single-pose `Model`, so an automatic reverse would risk destroying user data. Rolling back the *schema* is owned by 028's migration downgrade (which drops the columns wholesale).

## Data Persistence

| Table | Change | Detail |
|-------|--------|--------|
| `models` | INSERT (new rows) | One wrapper per legacy photo: `id` = `gen_random_uuid()`, `mayorista_id` copied, `name` = photo `label`, `created_at` = `now()` |
| `model_photos` | UPDATE (in place) | `model_id`, `pose='front'` set atomically per row; all other columns untouched (lossless) |

No DDL. No new indexes (selection uses existing `is_curated` index; `model_id IS NULL` scan is one pass, acceptable for a one-time migration).

## Security Design

| Concern | Approach |
|---------|----------|
| Authentication/Authorization | N/A — no API surface; runs with deploy DB credentials |
| Data isolation | Wrapper `mayorista_id` always copied from the photo's own `mayorista_id` — ownership invariant preserved; no cross-mayorista grouping |
| Data safety | Lossless (no DELETEs, no column rewrites besides the two link fields); curated rows never selected |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| Lock scope | Bounded 500-row reads and writes; transaction lifecycle remains owned by Alembic's `env.py` |
| Observability | Per-row debug log, per-batch info log, final `BackfillCompleted` summary (rows, batches, orphans skipped) |
| Runtime | Single O(n) pass; 500-row batches keep each transaction in the low-ms range for expected volumes |

## Error Handling

| Error Type | Behavior |
|------------|----------|
| Batch failure (e.g., constraint violation) | Alembic's managed migration transaction rolls back the migration; re-running safely selects only rows still lacking `model_id` |
| Empty table / nothing to do | First selection returns 0 rows → immediate success no-op |
| Orphaned rows (`mayorista_id IS NULL`) | Skipped, counted in summary |

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| PostgreSQL | All migration work | SQLAlchemy core via `op.get_bind()` inside Alembic revision |

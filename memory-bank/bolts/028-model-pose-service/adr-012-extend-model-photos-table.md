---
bolt: 028-model-pose-service
created: 2026-07-18T04:10:25Z
status: accepted
superseded_by: null
---

# ADR-012: Extend `model_photos` Table Instead of a Parallel Pose-Photo Table

## Context

The multi-pose VTON intent introduces the `Model` aggregate: a mayorista-owned identity grouping 1..3 pose-tagged photos (`front`/`side`/`back`). The platform already has a `model_photos` table (owned by the `001-media-service` bounded context) storing both curated library photos (`is_curated = true`) and mayorista-uploaded model photos used by single-image VTON flows.

Two options exist for pose photos: (a) extend `model_photos` with a nullable `model_id` FK and nullable `pose` column, or (b) create a new parallel `model_pose_photos` table. Any schema change must not break existing curated-library browsing or single-image VTON submission flows, which read `model_photos` today.

## Decision

Extend the existing `model_photos` table:

```python
# models/media.py — ModelPhoto (extended)
model_id = Column(
    UUID(as_uuid=True),
    ForeignKey("models.id", ondelete="CASCADE"),
    nullable=True,
    index=True,
)
pose = Column(String(10), nullable=True)  # 'front' | 'side' | 'back'
```

With database-level invariants:

```sql
ALTER TABLE model_photos ADD CONSTRAINT uq_model_photos_model_pose UNIQUE (model_id, pose);
ALTER TABLE model_photos ADD CONSTRAINT chk_model_photos_pose_values CHECK (pose IN ('front', 'side', 'back'));
ALTER TABLE model_photos ADD CONSTRAINT chk_model_photos_model_pose_coupling
    CHECK ((model_id IS NULL) = (pose IS NULL));
```

The coupling CHECK makes row semantics unambiguous: a row is either a curated/legacy photo (`model_id = NULL`, `pose = NULL`) or a pose photo belonging to a `Model` (both set). Curated rows are unaffected (PostgreSQL unique constraints allow multiple NULLs).

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Parallel `model_pose_photos` table** | Clean separation of pose photos; no changes to media-service table | Duplicates photo-storage columns (`mayorista_id`, `minio_key`, `uploaded_at`); curated and pose photos diverge — any future change to photo handling must be applied twice; legacy backfill (bolt 029) would require moving rows between tables | Duplication and double-maintenance outweigh separation benefits; backfill becomes a data move instead of an in-place UPDATE |
| **Extend `model_photos` (chosen)** | Single source of truth for model imagery; backfill is an in-place nullable-FK update; curated rows untouched; follows ADR-006 precedent for backwards-compatible cross-domain FK extension | Cross-domain schema dependency on media-service table; table now serves two row semantics (curated vs pose) | Best trade-off: minimal, reversible migration; zero impact on existing reads (new columns are nullable); invariants enforced at DB level |
| **JSONB `pose_metadata` column on `model_photos`** | No new columns/FK | No referential integrity on `model_id`; no DB-level uniqueness on `(model_id, pose)`; querying/indexing poses becomes expensive | Violates the relational design used everywhere else in the codebase |

## Consequences

### Positive

- Single table for all model imagery — curated library, legacy uploads, and pose photos share storage, validation, and presigned-URL conventions
- Bolt-029 backfill becomes an idempotent in-place UPDATE (`model_id`, `pose`) instead of a cross-table data move — lossless and reversible
- Zero impact on existing `001-media-service` reads: new columns are nullable, new constraints admit all existing rows
- DB enforces pose uniqueness and row-semantics coupling regardless of application bugs

### Negative

- Cross-domain schema dependency: `model_photos` now references `models` (mirrors ADR-006's accepted trade-off)
- `model_photos` carries two row semantics; every future query must be deliberate about `model_id IS NULL` filtering
- Migration must run before the pose endpoints are deployed

### Risks

- **Existing-row constraint violation on migration**: `chk_model_photos_model_pose_coupling` could fail if any row unexpectedly has one of the two fields set. Mitigation: new columns start NULL for all existing rows, so the CHECK passes by construction; verify with a data audit query in the migration.
- **Accidental full-table scans mixing semantics**: Mitigation: repository methods always filter explicitly (`model_id IS NULL` for curated/legacy paths, `model_id = :id` for pose paths).

## Related

- **Stories**: 001-create-model, 002-upload-pose-photo, 003-list-model-poses (bolt 028); 004-backfill-legacy-models (bolt 029)
- **Standards**: Should be noted in system-architecture.md under "Cross-domain schema references"
- **Previous ADRs**: ADR-006 (backwards-compatible nullable FK pattern), ADR-010 (unique constraint + fast-path pattern)

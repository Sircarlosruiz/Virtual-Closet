---
bolt: 023-batch-job-service
created: 2026-06-04T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-006: Backwards-Compatible batch_item_id FK on VtonJob

## Context

The batch job service needs to link individual `VtonJob` records to their parent `BatchItem` for completion callbacks. When a `VtonJob` completes, the callback must update the corresponding `BatchItem` status and increment batch counters. This requires a foreign key from `vton_jobs` to `batch_items`.

The `vton_jobs` table is owned by the `002-vton-job-service` domain and is used by existing single-item VTON submission flows. Any schema change must not break existing functionality — existing `VtonJob` records are created without a batch context and must continue to work unchanged.

## Decision

Add a nullable `batch_item_id` column to the `vton_jobs` table:

```python
# models/vton_job.py
batch_item_id = Column(
    UUID(as_uuid=True),
    ForeignKey("batch_items.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
```

**Migration strategy**:
1. Alembic migration adds column as nullable (no default)
2. Existing `VtonJob` records have `batch_item_id = NULL`
3. New `VtonJob` records created via batch flow set `batch_item_id`
4. Existing VTON job creation paths (`POST /api/vton/generate`) do not set this field
5. Completion callback checks `batch_item_id` — if `NULL`, skip batch update logic

**Code changes**:
- `models/vton_job.py`: Add `batch_item_id` column
- `services/vton_service.py`: Accept optional `batch_item_id` parameter in `create_and_enqueue()`
- Celery completion task: Check `if vton_job.batch_item_id: update_batch_item(...)`

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Separate mapping table** `batch_item_vton_job` | No schema change to `vton_jobs`, clean separation | Extra JOIN query on every completion callback; more complex migration | Unnecessary complexity for a 1:1 relationship |
| **Embed batch context in Celery task payload** | No schema change; task knows batch context | Payload not persisted; if task retries, batch context lost; harder to debug | Fragile — task payload is not a reliable data store |
| **Nullable FK on VtonJob** (chosen) | Simple, queryable, persisted, backwards-compatible | Schema change to another domain's table; requires coordination | Best trade-off: minimal impact, clear ownership (FK is nullable, existing code unaffected) |

## Consequences

### Positive

- Zero impact on existing VTON job creation flows — `batch_item_id` is nullable
- Completion callback can efficiently look up `BatchItem` via FK
- Queryable: can find all VTON jobs for a batch item, or all batch items for a VTON job
- Alembic migration is straightforward and reversible

### Negative

- Cross-domain schema dependency: `vton_jobs` table now references `batch_items`
- Requires coordination between batch and VTON job service teams (same codebase, but different bounded contexts)
- Migration must run before batch submission code is deployed

### Risks

- **Migration order**: If batch code deploys before migration, `batch_item_id` column doesn't exist and code fails. Mitigation: migration runs first in deployment pipeline; code checks column existence or uses feature flag.
- **Cascade delete behavior**: `ondelete="SET NULL"` ensures that if a `BatchItem` is deleted, the `VtonJob` is not deleted (it still needs to complete). This is intentional — VTON jobs outlive their batch context.

## Related

- **Stories**: 001-create-batch-job, 002-enqueue-batch-items, 003-track-item-status
- **Standards**: Should be noted in system-architecture.md under "Cross-domain schema references"
- **Previous ADRs**: None

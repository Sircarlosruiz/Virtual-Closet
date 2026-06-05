---
bolt: 025-batch-job-service
created: 2026-06-04T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-010: Unique Constraint on vton_job_id in Media Items for Idempotency

## Context

When a `BatchItem` completes, its result image is saved to the media library. The Celery callback may fire multiple times for the same `VtonJob` (e.g., due to network timeouts, duplicate signal delivery, or manual reprocessing). Without idempotency protection, duplicate callbacks would create duplicate media entries for the same result image.

Two approaches are available:
1. **Application-level check**: Before saving, check if `BatchItem.result_media_id` is already set. If set, skip the save.
2. **Database-level unique constraint**: Add a unique constraint on `media_items.vton_job_id`. The database rejects duplicate inserts, and the application catches the integrity error.

## Decision

Use **database-level unique constraint** on `media_items.vton_job_id` as the primary idempotency mechanism, with an application-level check as a fast-path optimization:

```python
# Schema change
ALTER TABLE media_items ADD CONSTRAINT uq_media_items_vton_job_id UNIQUE (vton_job_id);

# Application logic (fast-path)
async def save_result(self, batch_id, item_id, result_minio_key):
    if item.result_media_id is not None:
        return  # Fast-path: already saved
    
    try:
        media_item = await media_service.save(
            minio_key=result_minio_key,
            metadata={...},
            vton_job_id=vton_job_id,
        )
        await batch_repo.set_result_media(item_id, media_item.id)
    except IntegrityError:
        # Database rejected duplicate — another callback already saved
        logger.info("Duplicate media save for vton_job %s, skipping", vton_job_id)
```

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Application-level check only** | No schema change; simple logic | Race condition possible under concurrent callbacks; not crash-safe | Not sufficient — concurrent callbacks could both pass the check before either inserts |
| **Unique constraint only** (no fast-path check) | Database-enforced idempotency; race-condition safe | Every callback hits the database insert attempt (even duplicates) | Acceptable but wasteful — fast-path check avoids unnecessary DB round-trips |
| **Unique constraint + fast-path check** (chosen) | Best of both: race-condition safe + efficient for duplicates | Requires schema change; two layers of idempotency to maintain | Best trade-off: database guarantees correctness, application optimizes common case |

## Consequences

### Positive

- **Race-condition safe**: Unique constraint prevents duplicate inserts even under concurrent callbacks
- **Efficient**: Fast-path check avoids DB insert attempt for already-saved items
- **Clear error handling**: `IntegrityError` is unambiguous — another callback already saved the media item
- **Audit trail**: Failed duplicate inserts are logged, providing visibility into callback duplication

### Negative

- Schema change required: `ALTER TABLE media_items ADD CONSTRAINT uq_media_items_vton_job_id UNIQUE (vton_job_id)`
- Existing media items without `vton_job_id` must have NULL values (unique constraint allows multiple NULLs in PostgreSQL)
- Media service must accept `vton_job_id` parameter

### Risks

- **Migration on existing data**: If any `media_items` rows already have duplicate `vton_job_id` values, the migration will fail. Mitigation: run data audit before migration; clean up duplicates if found.
- **NULL uniqueness**: PostgreSQL allows multiple NULL values in a unique constraint, which is correct — non-batch media items have `vton_job_id = NULL`.

## Related

- **Stories**: 006-auto-save-to-media-library
- **Standards**: Should be noted in coding-standards.md under "Idempotency patterns"
- **Previous ADRs**: ADR-005 (transactional Celery publishing), ADR-009 (atomic counter updates)

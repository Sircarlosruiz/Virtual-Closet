---
bolt: 029-model-pose-service
created: 2026-07-18T05:12:30Z
status: accepted
superseded_by: null
---

# ADR-042: Bounded Batch Processing for Alembic Data Migrations

## Context

The legacy `ModelPhoto` backfill must UPDATE potentially many rows. Alembic's default behavior on PostgreSQL is to wrap the entire migration in a single transaction ("Will assume transactional DDL"). For a data migration touching a large table, that means one long-lived transaction holding write locks for the full duration — blocking concurrent API writes (pose uploads from bolt 028's endpoints) and risking lock contention during deploy.

The migration also must be safe to resume: if it fails midway, already-processed rows should not need reprocessing, and re-running must not duplicate work.

## Decision

Use bounded batch processing for large-table data migrations. The current
project runner keeps one transaction around `context.run_migrations()`, so
revisions must not call `commit()` internally. Each iteration reads and writes
at most `BATCH_SIZE` rows, and the idempotent predicate makes a rerun safe:

```python
BATCH_SIZE = 500

def upgrade() -> None:
    bind = op.get_bind()
    while True:
        rows = bind.execute(select_legacy_rows.limit(BATCH_SIZE)).fetchall()
        if not rows:
            break
        for row in rows:
            # INSERT wrapper ... RETURNING id
            # UPDATE photo SET model_id, pose='front' ... AND model_id IS NULL
            pass
        # Next loop iteration re-selects only still-unlinked rows.
```

Three properties are mandatory when using this pattern:

1. **Managed transaction**: revisions must use the transaction supplied by `env.py` and must not call `commit()` internally.
2. **Idempotent selection predicate**: each batch re-selects only unprocessed rows (`model_id IS NULL ...`), so completed batches are never revisited — this is what makes resume-after-failure safe.
3. **Atomic row link**: the per-row UPDATE includes a redundant guard (`AND model_id IS NULL`) so concurrent writers cannot produce a half-updated or double-linked row.

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Single unbounded query** | Simple | Loads all candidate rows at once and increases memory/statement duration | Unbounded result set is avoidable |
| **Management command / standalone script** | Full control over transactions | Not automatic at deploy; easy to forget; drift between environments | Story explicitly requires automatic deploy-integrated execution |
| **Bounded batch processing (chosen)** | Bounded memory and statement size; resume-safe; automatic at deploy | Current runner still owns one transaction, so total lock duration remains migration-wide | Best compatible trade-off without changing the shared migration runner |

## Consequences

### Positive

- Memory and statement scope are bounded to 500 candidate rows per iteration
- Resume-after-failure is safe: the managed transaction rolls back consistently, and re-running uses the idempotent selection predicate
- Reusable template for any future large-table data migration in this project

### Negative

- The current runner retains one transaction for the migration; very large datasets may require a future runner change for independently committed batches
- Partial visibility is not available until the Alembic transaction commits

### Risks

- **Long deploy window on very large tables**: the batch size can be tuned; independently committed batches require a deliberate migration-runner change.

## Related

- **Stories**: 004-backfill-legacy-models
- **Standards**: Candidate for coding-standards.md under "Migrations — data migrations"
- **Previous ADRs**: ADR-010 (idempotency via DB guard + fast-path), ADR-041 (no-op downgrade convention)

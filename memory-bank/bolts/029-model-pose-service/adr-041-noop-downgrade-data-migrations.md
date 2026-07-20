---
bolt: 029-model-pose-service
created: 2026-07-18T05:12:30Z
status: accepted
superseded_by: null
---

# ADR-041: No-Op Downgrade for Backfill-Type Data Migrations

## Context

The legacy `ModelPhoto` backfill (Alembic revision `b7c8d9e0f1a2`) creates one wrapper `Model` row per legacy photo and links them. A question arises for every data migration of this kind: what should `downgrade()` do?

Reversing the operation would mean deleting wrapper `Model` rows and unlinking the photos. But after deploy, a wrapper `Model` (one `front` pose, mayorista-owned, name from a photo label) is **indistinguishable** from a `Model` a user created manually through the API with a single front pose. There is no marker column separating "backfill-created" from "user-created" rows — and adding one solely for downgrade purposes would permanently widen the schema for a one-time event.

## Decision

Data migrations that create parent/identity rows (backfills, wrapper creation, entity synthesis) are **intentionally irreversible**: `downgrade()` is a no-op with a comment explaining why. Schema rollback remains the responsibility of the owning *schema* migration (here: 028's `f1e2d3c4b5a6` downgrade, which drops the `model_id`/`pose` columns wholesale).

Do **not** add marker columns (`created_by_backfill`, etc.) to enable reversal — the schema cost is permanent, the benefit is one-time.

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Full reverse: unlink photos + delete wrappers** | Clean rollback of the data change | Cannot distinguish wrapper Models from user-created single-pose Models → risks destroying real user data created after deploy | Unacceptable data-loss risk |
| **Marker column to identify backfill rows** | Enables precise reversal | Permanent schema widening for a one-time migration; every future query pays for it | Cost/benefit is clearly negative |
| **No-op downgrade (chosen)** | Zero data-loss risk; honest about irreversibility; simple | `alembic downgrade` across this revision does not undo the data change (documented) | Correct trade-off for identity-creating data migrations |

## Consequences

### Positive

- Zero risk of deleting user-created data on rollback
- Rollback semantics are explicit and documented in the migration file itself
- Sets a clear convention: schema migrations own schema rollback; data migrations document data irreversibility

### Negative

- `alembic downgrade` past this revision leaves backfilled data in place (wrappers + links persist) — operators must understand downgrade is schema-only here
- If a true data reversal is ever needed, it requires a new forward migration with explicit selection logic

### Risks

- **Operator surprise during rollback**: Mitigation: the migration's `downgrade()` contains a comment stating it is a no-op and why; this ADR records the convention.

## Related

- **Stories**: 004-backfill-legacy-models
- **Standards**: Candidate for coding-standards.md under "Migrations"
- **Previous ADRs**: ADR-012 (the coupling CHECK this migration satisfies), ADR-006 (nullable FK precedent)

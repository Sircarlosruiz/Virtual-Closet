---
bolt: 054-photoshoot-orchestration
created: 2026-09-19T17:01:00Z
status: proposed
superseded_by: null
---

# ADR-071: Photoshoot Idempotency Unique Is the Key, Not (Key, Fingerprint)

## Context

FR-12 requires that repeating `POST .../photoshoots` with the same `Idempotency-Key` and the same body returns the existing photoshoot, and that the same key with a different body returns `409`. Bolt 053 persisted `idempotency_key` and `payload_fingerprint` with **no** unique index: two POSTs created two rows.

Bolt 044 already solved the same HTTP header for `GenerationJob` with a **composite** unique index on `(idempotency_key, payload_fingerprint) WHERE idempotency_key IS NOT NULL`. Conflict (same key, different fingerprint) is detected in `IdempotencyService`, not by the database. That index **allows** two rows with the same key and different fingerprints: under concurrent POSTs the 409 is a race, and the database will accept both inserts.

A photoshoot is more expensive than a single generation job (M×N provider calls). A lost race here duplicates Replicate work and gallery images. The reservation is also scoped to a product (`ProductLink`), not to the whole tenant: BFashion may reuse the same key string on another product.

## Decision

Enforce at most one photoshoot per `(product_link_id, idempotency_key)` when the key is present:

```text
UNIQUE (product_link_id, idempotency_key) WHERE idempotency_key IS NOT NULL
```

Lookup is by that pair. Same fingerprint → replay (same `photoshoot_id`, no enqueue). Different fingerprint → `409 IDEMPOTENCY_CONFLICT`, no new row. Missing header → no reservation (`unprotected`).

Under insert collision (`IntegrityError`), re-read the winner and apply the same replay-or-409 rule.

`product_link_id` is already a global UUID; `tenant_id` is not part of the index. Callers always resolve the link for the authenticated `ServiceClient` before touching the reservation.

This does **not** change `generation_jobs`. ADR-044's composite unique stays on that table.

## Rationale

The invariant FR-12 names is “one photoshoot per key for this product,” not “one photoshoot per (key, body).” The 409 is the conflict outcome of **one** reservation, not a second row. Putting uniqueness on the key makes the database the mutex; the fingerprint is only the comparison payload.

Scoping to `product_link_id` keeps BFashion's keys local to the resource they POST to, matching how the GET is nested under `external_product_id`.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| UNIQUE on `(product_link_id, idempotency_key)` (chosen) | Race-closed 409; one row per key; product-scoped | Duplicate 053 rows must be nulled before the index | Selected |
| Copy 044: UNIQUE `(key, fingerprint)` + service 409 | Familiar; no cleanup of fingerprint-distinct twins | Two rows with the same key can commit; second enqueue | Violates FR-12 under concurrency |
| UNIQUE on `idempotency_key` globally | Simpler index | Cross-product mutex; false 409 between SKUs | Keys are caller tokens, not tenant secrets |
| UNIQUE `(tenant_id, key)` | Tenant-wide replay | Still collides two products; extra column in the index | The path already identifies the product |
| Application-only check, no unique | No migration | Two concurrent creates both pass the SELECT | NFR-5 requires a DB guard (ADR-010 / ADR-054) |

## Consequences

### Positive

- Concurrent retries cannot create two photoshoots for the same product key.
- 409 is deterministic: the row already exists, the fingerprint disagrees.
- Replay of `failed` / `partial` / `completed` has a single identity to return; no relaunch.

### Negative

- Intentional deviation from the `generation_jobs` index shape. Agents must not copy 044 onto `photoshoots`.
- Alembic must neutralize 053 duplicates (keep oldest `created_at`, NULL later keys) before creating the index.

### Risks

- **Risk**: NULLing duplicate keys leaves those later rows unprotected. **Mitigation**: they were accidental twins; V1 has no production traffic yet. Document as one-way (downgrade drops the index, does not restore keys).
- **Risk**: Callers using one key across products expect a tenant-wide replay. **Mitigation**: contract C is nested under `external_product_id`; same string on another product is a different reservation by design.

## Related

- **Stories**: 005-photoshoot-idempotency-and-retry
- **Standards**: Idempotency of contract-C POSTs; Alembic additive unique indexes
- **Previous ADRs**: ADR-010, ADR-044 (044 design), ADR-054, ADR-048

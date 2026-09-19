---
bolt: 054-photoshoot-orchestration
created: 2026-09-19T17:01:00Z
status: proposed
superseded_by: null
---

# ADR-072: Photoshoot Idempotency Uses the Shared Fingerprint, Not IdempotencyService

## Context

The unit brief and story 005 say to reuse `IdempotencyService` and `compute_payload_fingerprint`, which already implement “same key + same body → same work; same key + different body → 409” for `GenerationJob`.

`IdempotencyService` (bolt 044) is built around that aggregate: lookup and create go through `GenerationJobRepository`, and uniqueness is the composite `(idempotency_key, payload_fingerprint)` that ADR-071 explicitly **rejects** for photoshoots.

`compute_payload_fingerprint` is a pure function: stable canonical JSON → hash, independent of which table stores the result. That is the part FR-12 actually shares.

Generalizing `IdempotencyService` into a protocol over “any root with key+fingerprint” would touch the image-generation path in the same bolt that must only add GET, replay, and `variant_key`. A third, hand-rolled `hashlib.sha256(json.dumps(body))` would drift from 044 (key order, list sorting, null overlay).

## Decision

1. **Reuse** `compute_payload_fingerprint` as the only fingerprint algorithm. Canonical body for a photoshoot is defined in bolt 054's technical design (sorted `model_ids` / `pose_ids`, empty overlay ≡ null, no `Idempotency-Key`, no `system` / `tenant_id`).
2. **Do not** call `IdempotencyService.resolve_or_create` for photoshoots. Add `PhotoshootIdempotencyService` that reads/writes via `PhotoshootRepository` and applies ADR-071 (lookup by `product_link_id` + key; compare fingerprint; UNIQUE collision → re-read).
3. **Do not** extract a generic idempotency protocol in this bolt. If a later contract-C POST needs the same shape, extract then, with ADR-071's unique-on-key rule as the default for expensive orchestrations.

`submit` validates the Pydantic body **before** touching the reservation so a malformed JSON cannot 409 against a healthy key.

## Rationale

Same hash, different aggregate, different unique constraint. Wiring photoshoots through a job-typed service would either create `GenerationJob` rows that are not photoshoots or force a breaking generalization of 044 under time pressure.

A thin photoshoot service is testable without the generation repository and makes the 409 path obviously “no enqueue.”

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Shared fingerprint + photoshoot service (chosen) | One hash; ADR-071 unique; no 044 refactor | Two small services with the same outcomes | Selected |
| Call `IdempotencyService` as-is | One class | Bound to `GenerationJob` and composite unique; wrong row type | Would create or collide jobs, not photoshoots |
| Generic `IdempotencyService[T]` now | DRY for future C POSTs | Scope creep; rewrites a working 044 path | Extract when a third caller exists |
| New ad-hoc SHA-256 in submit | Fast to type | Third algorithm; key-order bugs; 409 mismatch vs jobs | Forbidden by the domain model |
| Fingerprint includes `external_product_id` | Path in the hash | Redundant with ADR-071 scope; rename of the product id would 409 a replay | Scope is the resolved link |

## Consequences

### Positive

- Photoshoot replay cannot accidentally enqueue a `GenerationJob` try-on.
- Fingerprints stay comparable across the platform (same helper, same stability tests).
- 044 remains untouched.

### Negative

- Two resolve-or-replay implementations to keep in semantic sync (outcomes: created / replayed / conflict / unprotected).
- Future authors may copy the photoshoot service instead of extracting the protocol.

### Risks

- **Risk**: Canonical photoshoot dict drifts from what BFashion actually sends (e.g. `pose_ids` vs `pose_count`). **Mitigation**: fingerprint the **validated** body; tests lock sorted lists and overlay-empty ≡ null.
- **Risk**: Someone later points submit at `IdempotencyService` “to reuse FR-12.” **Mitigation**: this ADR; code comment on `PhotoshootIdempotencyService` pointing at ADR-071/072.

## Related

- **Stories**: 005-photoshoot-idempotency-and-retry
- **Standards**: Contract-C POST idempotency; `compute_payload_fingerprint`
- **Previous ADRs**: ADR-071, ADR-044 (044 design), ADR-047, ADR-048

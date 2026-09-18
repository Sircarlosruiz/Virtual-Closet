---
bolt: 046-template-composition
created: 2026-09-17T22:34:52Z
status: proposed
superseded_by: null
---

# ADR-054: Deterministic Spec-Hash Idempotency Enforced at the Database

## Context

Story 003 requires that recomposing an unchanged SKU/style does not produce a
no-op duplicate, and that identical inputs always yield the same output. If
idempotency were checked only in the service layer ("does a version with this
spec already exist?"), two concurrent compose requests for the same overlay
could both pass the check and append duplicate versions — or two byte-identical
renders could be stored under different version numbers, breaking the
determinism guarantee.

Determinism also depends on the font/renderer, not just the spec: upgrading the
font file silently changes rendered pixels. Any idempotency key must therefore
include the font identity, or a font upgrade would be mistaken for "same
input".

## Decision

Compute `spec_hash = sha256(normalized_sku, placement, style, base_image_key,
font_version)` and enforce `UNIQUE (overlay_id, spec_hash)` on
`composition_versions`. A compose request whose `spec_hash` already exists
returns the existing version (`200`) instead of appending a new one. The
`font_version` is derived from the pinned font file plus the renderer version
and is stored on every version.

## Rationale

A database unique constraint closes the race window outright: at most one row
can exist per deterministic input, regardless of concurrent requests. The
service still checks first for the fast path, but correctness does not depend
on that check. Including `base_image_key` ensures the same SKU on a different
base image is a different composition, and including `font_version` makes
renderer/font upgrades produce a *new* version rather than silently mutating
the meaning of an existing `spec_hash`.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Hash + DB unique constraint (chosen) | Race-safe by construction; deterministic and auditable | A hash column is opaque; font upgrades intentionally create new versions | Correctness guarantee outweighs a small opaque column |
| Service-layer existence check only | Simple, no new constraint | Race window under concurrency; no schema-level guarantee | Two concurrent composes could duplicate a version |
| Compare full spec JSONB equality | No separate hash column | JSONB equality semantics are fragile (key order, numeric form); no single index target | Hash normalizes the spec into a stable key |
| Exclude font_version from the hash | Stable versions across font upgrades | A font upgrade would silently change rendered bytes for the same key, violating "immutable output" | Directly breaks determinism |

## Consequences

### Positive

- Byte-identical outputs are guaranteed to share one row; no duplicate versions.
- Concurrent compose requests are safe at the database level.
- Font/renderer upgrades are explicit, auditable events (a new version).
- `spec_hash` is a cheap lookup key for the common recompose path.

### Negative

- A hash column is not human-readable; debugging requires recomputing the hash.
- Determinism is only as stable as the pinned font/renderer; any change
  invalidates the prior hash (by design, but requires discipline).

### Risks

- **Risk**: The normalizer or spec serialization changes format (e.g. key
  order, whitespace), changing the hash for an otherwise identical spec.
  **Mitigation**: The hash is computed over a canonical, documented
  serialization; Stage 5 tests assert a fixed fixture hash so accidental
  format changes fail loudly.

## Related

- **Stories**: 003-deterministic-sku-composition
- **Standards**: None.
- **Previous ADRs**: ADR-052 (Immutable, Copy-Not-Reference Composition
  Snapshot) — shares the "constraint enforced at the database" principle.

---
bolt: 050-bridge-provisioning
created: 2026-09-19T00:40:02Z
status: proposed
superseded_by: null
---

# ADR-058: `StaffIdentityLink` Is the Only Mirror Signal

## Context

Each BFashion staff user needs a `Mayorista` row so `_authorize_staff` can
resolve the asserted UUID (ADR-019: we extend/reuse `Mayorista`, we do not
add a `User` table). That row is a **mirror**: it is not a usable login
(unrecoverable password hash, no secret in the API).

OQ-5 asks whether mirrors consume the tenant's monthly wholesaler quota
(`LimiteMensualAlcanzadoError`). If they do, provisioning N staff can exhaust
a limit meant for real wholesalers. The domain model answers **no**.

Later bolts (intake, photoshoot, catalog) will see
`product_link.mayorista_id` and must be able to ask "is this a mirror?"
without inventing a second convention.

## Decision

Do **not** add `is_bridge_mirror` (or any kind/flag column) on `mayoristas`.

A `Mayorista` is a mirror **if and only if** a `staff_identity_links` row
points at it (`mayorista_id`). Quota, login, and any "real wholesaler"
filter in later bolts must use that membership (or a repository helper
built on it). This bolt does not change `prenda_service` quota code; it
only establishes the signal those callers must use.

## Rationale

A boolean on `mayoristas` would denormalize a fact already owned by the
new aggregate and invite drift (flag true, link revoked; link present,
flag false). ADR-019 already warns against growing `Mayorista` unless the
column is about mayorista-as-account. Mirror-ness is a bridge-provisioning
fact, not an auth-account fact.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Membership in `staff_identity_links` (chosen) | Single source of truth; no Mayorista migration; matches the new aggregate | Later quota queries need a join or `EXISTS` | Join is cheap (indexed `mayorista_id`); cost sits on rare quota paths |
| `mayoristas.is_bridge_mirror` | Cheap filter on hot quota queries | Second source of truth; Alembic on a core table; easy to forget on revoke/reactivate | Denormalization for a V1 path that does not even charge quota |
| Separate `BridgeStaff` table instead of `Mayorista` | Clear type | `_authorize_staff` would have to change | Frozen contract; ADR-019 |
| Mirrors consume quota like real wholesalers | No special case | Mass provisioning burns commercial limits | OQ-5 proposal rejected this |

## Consequences

### Positive

- `Mayorista` schema stays stable (ADR-019).
- Revoke/reactivate only mutates `StaffIdentityLink`; quota eligibility
  follows `is_active` without a second write.
- OQ-5 has an implementable rule: skip quota when `EXISTS staff_identity_links
  WHERE mayorista_id = :id`.

### Negative

- Callers that only have a `mayorista_id` must consult another table.
- A future engineer may still add the boolean "for performance" and fork
  the meaning of mirror.

### Risks

- **Risk**: Photoshoot/prenda code charges quota against
  `product_link.mayorista_id` (the mirror). **Mitigation**: this ADR's
  "Read when" plus unit 001 notes; 051/053 must not introduce quota on
  that id without an explicit product change.

## Related

- **Stories**: 002-staff-identity-provisioning, 003-staff-identity-revocation
- **Standards**: Quota and mayorista-kind checks
- **Previous ADRs**: ADR-019 (extend Mayorista), ADR-001 (mirror is not a
  login context)

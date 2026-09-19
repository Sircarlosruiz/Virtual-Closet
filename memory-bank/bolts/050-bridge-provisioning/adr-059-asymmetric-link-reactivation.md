---
bolt: 050-bridge-provisioning
created: 2026-09-19T00:40:02Z
status: proposed
superseded_by: null
---

# ADR-059: Asymmetric Reactivation of Product Links vs Staff Identities

## Context

Both aggregates are unique on `(system, external_*_id)` and carry `is_active`.
Idempotent create on a unique pair must define what happens when the existing
row is **inactive**.

- Story 001: a `ProductLink` with `is_active = false` returns **409**;
  create must not reactivate. Reactivation is a different operation, out of
  scope.
- Story 002: re-provisioning a previously revoked `external_staff_id`
  returns the **same** `staff_id`, sets the link active again, `created=false`.
  A second Mayorista must never be created.

Treating both tables with the same "create = upsert including reactivate"
helper would violate 001. Treating both with "create never reactivates"
would violate 002 and force BFashion to mint a new UUID after every revoke
(or add a dedicated reactivate endpoint that FR-2 does not have).

## Decision

**Asymmetric by design:**

- `ProductLink.create_link`: inactive existing row → conflict (409
  `PRODUCT_LINK_INACTIVE`). No column change.
- `StaffIdentityService.provision`: inactive existing row → reactivate
  (`is_active=true`, `revoked_at=null`), same `mayorista_id`, HTTP 200,
  `created=false`.

Do not share a generic "idempotent upsert" that hides this difference.

## Rationale

A product link being off is an ownership/authorization state: turning it
back on is a deliberate ops action (not in V1). A staff identity being off
is "this person must not act"; the person is still the same person. FR-2
makes re-provision the reactivate path so `manage.py link_staff_identity`
stays a single call.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Asymmetric rules (chosen) | Matches both stories; no extra staff endpoint | Two tables that look alike behave differently | Documented here so implementers do not "simplify" |
| Create never reactivates either | Symmetric code | Staff would need `POST ...:reactivate` or a new UUID after revoke | Breaks FR-2 / story 002 edge case |
| Create reactivates both | Symmetric code | Silent re-enable of a deactivated product link | Breaks story 001; security/ownership surprise |
| 409 on revoked staff, separate reactivate | Explicit | Extra contract for intent 020 | FR-2 already defined one provision endpoint |

## Consequences

### Positive

- BFashion re-links a returning staff member with the same command and UUID.
- A deactivated product cannot come back as a side effect of a create retry.
- Historical FKs stay valid because the Mayorista row is reused.

### Negative

- Helpers that "upsert by unique pair" are unsafe across these two tables.
- Reviewers must remember the split; the schemas look parallel on purpose
  (unit brief) which makes the behavioral difference easy to miss.

### Risks

- **Risk**: Implementation copies `create_link` collision handling onto
  provision and returns 409 after revoke. **Mitigation**: story 002 edge
  case is a required test; this ADR is listed in the implement stage
  constraints.

## Related

- **Stories**: 001-product-link-creation, 002-staff-identity-provisioning,
  003-staff-identity-revocation
- **Standards**: Idempotent create vs reactivate
- **Previous ADRs**: ADR-054 / ADR-010 (uniqueness is the idempotency
  authority; they do not define inactive-row semantics)

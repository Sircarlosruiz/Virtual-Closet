---
bolt: 050-bridge-provisioning
created: 2026-09-19T00:40:02Z
status: proposed
superseded_by: null
---

# ADR-057: Contract-C Staff Resolution Lives Outside `_authorize_staff`

## Context

The existing BFashion bridge (contract B, bolts 047/048) authorizes an asserted
`staff_id` through `integration_service._authorize_staff`: the UUID must exist
as a `Mayorista`, belong to the caller's tenant, and have a role in
`STAFF_ROLES = {admin, owner, staff}`. That function does not know about
`StaffIdentityLink` and must not be rewritten — unit 001 and stories 002/003
freeze `integration_service.py` so the mirror is built to satisfy the current
rule, not the other way around.

Contract C (this intent) adds revocation. After a mirror is revoked the
`Mayorista` row stays (historical FKs on `product_links.created_by` and
`publication_selections.selected_by`). `_authorize_staff` would still accept
that UUID. Every new C endpoint must reject it with 403, and that check must
not be copy-pasted into each router (story 003).

## Decision

Introduce `StaffIdentityService.resolve_staff_identity(client, staff_id)` as
the **only** staff gate for contract C. It applies, in order:

1. `Mayorista` exists
2. `mayorista.tenant_id == ServiceClient.tenant_id`
3. `mayorista.role ∈ STAFF_ROLES` (import the constant; do not edit the module)
4. An **active** `StaffIdentityLink` exists for `(system, tenant_id, mayorista_id)`

`POST /product-links` in this bolt, and every later C command that asserts
`staff_id` (presign, confirm, photoshoot submit), must call this method.
`integration_service.py` is not modified. Contract B may continue to accept a
revoked mirror; that is an accepted split until a later intent chooses to
unify the paths.

## Rationale

C needs a rule B does not have (link activity). Changing `_authorize_staff`
would either break the freeze or silently change B's behavior. A new service
keeps B stable, gives C a single callsite, and leaves a documented seam if
we later want B to honor revocation too.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| New `resolve_staff_identity` (chosen) | B untouched; one gate for all C commands; testable in isolation | Two authorization paths; a future C router can forget the call | Forgetfulness is cheaper to catch with a C-wide test than a B regression |
| Extend `_authorize_staff` to require an active link | One function for B and C | Edits a frozen module; B starts rejecting revoked mirrors without a B story | Violates the unit constraint and changes shipped behavior |
| Duplicate the check in each C router | No new service | Easy to miss on 051/053/056 | Story 003 forbids this |
| Wrap `_authorize_staff` then add the link check | Reuses the exact B predicate | Depends on a likely-private method; still a second path | Importing `STAFF_ROLES` is enough and does not couple to a private API |

## Consequences

### Positive

- Revocation is enforced everywhere C asserts a staff actor, without rewriting B.
- 051, 053, and later C commands have an obvious dependency: call
  `resolve_staff_identity`, do not reimplement.
- `_authorize_staff` remains the compatibility contract the mirror is built for.

### Negative

- B and C diverge after revoke: the same UUID can be valid on B and forbidden
  on C.
- The C gate is service-layer only (same class of risk as ADR-051): a new
  router that calls `_authorize_staff` directly will ignore revocation.

### Risks

- **Risk**: A later C endpoint uses `_authorize_staff` and accepts a revoked
  staff. **Mitigation**: Story 003's criterion ("any C endpoint → 403") is
  re-tested in each C bolt; code review treats a raw `_authorize_staff` call
  from a C router as a defect.

## Related

- **Stories**: 002-staff-identity-provisioning, 003-staff-identity-revocation,
  001-product-link-creation
- **Standards**: Contract C authorization should be noted next to the
  integration router conventions
- **Previous ADRs**: ADR-001 (separate auth contexts), ADR-012 (tenant
  isolation)

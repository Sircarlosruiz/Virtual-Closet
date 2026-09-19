---
bolt: 050-bridge-provisioning
created: 2026-09-19T00:40:02Z
status: proposed
superseded_by: null
---

# ADR-060: `ProductLink.mayorista_id` Is the Staff Mirror

## Context

`ProductLink` already stores the Virtual Closet owner as `mayorista_id`.
Bolt 047 resolved that owner from an explicit, pre-provisioned mapping.
This bolt must set `mayorista_id` on **create**, and FR-1 / story 001 say
it is resolved from the staff mirror and the `ServiceClient` tenant — never
from a SKU or other external id.

BFashion also has an optional `external_wholesaler_id`. A natural reading
is "the company owns the product, the staff member acts". Catalog (FR-16),
generation jobs (`owner_id = product_link.mayorista_id`), models, and
private templates are all scoped by mayorista. If each staff mirror becomes
the link owner, those scopes become **per staff**, not per company.

V1 is a single tenant (product decision). There is no separate "company
Mayorista" API in this unit. Inventing one here would block the root bolt
on an unscoped identity.

## Decision

On `create_link`, `ProductLink.mayorista_id =` the `Mayorista.id` of the
**active staff mirror** returned by `resolve_staff_identity`.
`created_by` is the same UUID. `external_wholesaler_id`, if present, is
stored for fail-closed comparison with later resolve calls; it does **not**
select a different owner.

This is a V1 identity model: the actor who created the link *is* the owner
the rest of the bridge will see. A later intent may introduce a company
mayorista and a migration; it must not be assumed by 051/053/056.

## Rationale

The stories are explicit and the unit has no other owner to point at.
Using `external_wholesaler_id` to invent or look up a second Mayorista
would reintroduce the "infer owner from an external id" invariant that
`ProductLink` exists to forbid.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Owner = staff mirror (chosen) | Matches FR-1; no extra entity; create stays one round-trip | Catalog/models/jobs are per-staff; two staff can own two links for the "same" company | V1 single-tenant; no company-mayorista provision API |
| Owner = a tenant-level company Mayorista | Matches wholesaler mental model | Who creates that row? Cross-staff catalog needs it now | Out of unit scope; would block 050 |
| Owner inferred from `external_wholesaler_id` | Familiar to BFashion | Breaks the "never infer owner from an external id" invariant | Core fail-closed rule of ProductLink |
| Nullable `mayorista_id` until a company is linked | Flexible | Breaks 047 resolve and job `owner_id` | Existing column is the owner |

## Consequences

### Positive

- Create is deterministic: one resolved staff → one owner.
- `_authorize_staff` and `resolve_staff_identity` see the same UUID the
  link stores as owner/`created_by`.
- 051/053/056 can keep using `product_link.mayorista_id` without a second
  lookup in V1.

### Negative

- Private templates and models keyed by mayorista will not automatically
  be shared across staff of the same BFashion org.
- Quota (ADR-058) and ownership metrics that assume "mayorista = company"
  will mis-count unless they honor the mirror signal.

### Risks

- **Risk**: Photoshoot catalog (056) looks empty for staff B because
  models live under staff A's mirror. **Mitigation**: call out in 056
  design; product may later add a company mayorista. Do not silently
  widen `mayorista_id` in 050.

## Related

- **Stories**: 001-product-link-creation, 002-staff-identity-provisioning
- **Standards**: ProductLink ownership invariant
- **Previous ADRs**: ADR-058 (mirror signal), ADR-057 (staff resolution),
  ADR-012 (tenant still comes from ServiceClient)

---
bolt: 051-source-image-intake
created: 2026-09-19T01:48:00Z
status: proposed
superseded_by: null
---

# ADR-061: Scoped Source-Image Misses Return 403, Not 404

## Context

ADR-040 says ownership-scoped endpoints return `404` when a resource is missing or belongs to someone else, so the caller cannot probe existence. That rule is the default for mayorista-scoped cookie APIs.

Contract C source-image confirm is nested: the caller already resolved a `ProductLink` via `external_product_id`, then names a `source_image_id`. Story 003 requires two things at once:

1. Confirming another product's reservation returns **403** and does not register media.
2. A foreign reservation and a nonexistent id must look **the same** from outside.

If this bolt used ADR-040 literally (`404` for unowned, `404` for missing), it would match the spirit but contradict the story's status code. If it used `403` for foreign and `404` for missing, it would leak whether that UUID exists.

Product-link resolution is a different resource: the path already carries `external_product_id`. For an unresolvable product (absent, inactive, other tenant, other wholesaler) the design keeps **404** `PRODUCT_LINK_NOT_FOUND` — that is ADR-040 applied to the product, not to the reservation.

## Decision

Once a `ProductLink` has been resolved for the caller, any `source_image_id` that is not an owned row of **that** link and **that** tenant returns **403** `SOURCE_IMAGE_FORBIDDEN` with a generic body.

This includes:

- the id does not exist
- the id exists on another `product_link` (same tenant or not)
- the id exists but `tenant_id` does not match the `ServiceClient`

Do **not** return 404 for those reservation misses. Do **not** distinguish them.

Product-scope failures stay 404 `PRODUCT_LINK_NOT_FOUND`. Staff failures stay 403 `STAFF_FORBIDDEN` (FR-15). Unauthenticated stays 401.

Bolt 053 (photoshoot submit that references `source_image_id`) must reuse this opacity: a `source_image_id` that is not `ready` **and owned by this link** must not become an existence oracle. Status for "not usable" (`pending` / `rejected` owned by this link) is a different case (`422` per FR-5) because the caller already minted that id.

## Rationale

The story text is the acceptance contract BFashion will test against. Opacity is the security invariant; 403 is the code the story named. One code for both misses is what prevents the oracle.

ADR-040 remains the default **when the path id is the resource being hidden**. Here the path id that would leak is `source_image_id` *after* the product is already in scope, so a dedicated rule is clearer than stretching ADR-040 until it contradicts the story.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| 403 for owned-scope misses (chosen) | Matches story 003; foreign ≡ missing | Diverges from ADR-040's 404 habit | Story + opacity beat consistency of status number |
| 404 for owned-scope misses (pure ADR-040) | One platform rule | Fails the explicit 403 criterion | Would fail story 003 as written |
| 403 foreign / 404 missing | Familiar REST | Existence leak | Forbidden by story 003 and FR-15 |
| 404 for product *and* reservation | Simpler table | Same story-code problem | Product 404 is enough for ADR-040 |

## Consequences

### Positive

- BFashion can treat "this id is not confirmable on this product" as a single client branch.
- Cross-product probing does not reveal whether a UUID was issued.
- 053 has a written rule instead of re-litigating 403 vs 404.

### Negative

- Two "not found" shapes on the same URL prefix: product 404 vs reservation 403.
- Clients and future routers must not "fix" reservation misses back to 404 in the name of ADR-040.

### Risks

- **Risk**: A later C endpoint returns 404 for an unowned `source_image_id` and reopens the oracle. **Mitigation**: story 003-style tests in 051 and 053; code review treats a 404 on a scoped source-image id as a defect unless the product itself failed to resolve.

## Related

- **Stories**: 002-source-image-confirm, 003-source-image-rejection
- **Standards**: Contract C error taxonomy next to integration router conventions
- **Previous ADRs**: ADR-040 (404 for unowned — still used for ProductLink resolution), ADR-012 (tenant from ServiceClient), ADR-057 (staff 403 is a separate gate)

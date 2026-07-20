---
bolt: 028-model-pose-service
created: 2026-07-18T04:10:25Z
status: accepted
superseded_by: null
---

# ADR-013: Return 404 (Not 403) for Unowned Resource Access

## Context

The model-pose endpoints (`POST /api/models/{id}/poses`, `GET /api/models/{id}/poses`) operate on resources owned by a specific mayorista. When mayorista A requests a `Model` belonging to mayorista B (or a nonexistent ID), the API must choose between:

- `403 Forbidden` — "the resource exists but you may not access it" (leaks existence)
- `404 Not Found` — "no such resource" (indistinguishable from a truly missing ID)

Story 003's edge cases explicitly require 404 for cross-mayorista access. This decision affects every ownership-scoped endpoint in the API, so it is recorded as a convention rather than a per-endpoint detail.

## Decision

All ownership-scoped endpoints **return `404 Not Found` when the resource does not exist *or* exists but belongs to a different mayorista**. Ownership is enforced inside repository queries (`WHERE id = :id AND mayorista_id = :session_mayorista_id`), so an unowned resource is genuinely "not found" from the caller's perspective — the service layer raises `ModelNotFoundError` and the router translates it to 404 with a generic body (`{"detail": "Model not found"}`).

403 is reserved for cases where the resource is legitimately visible to the caller but the *action* is forbidden (e.g., subscription-gated features) — a distinction that does not arise in this bolt.

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **403 for unowned resources** | Semantically precise; easier debugging for integrators | Confirms resource existence to any authenticated user — enables ID enumeration/oracle attacks against competitor mayoristas' data | Information disclosure outweighs semantic purity |
| **404 for unowned resources (chosen)** | No existence leak; unowned and nonexistent are indistinguishable; ownership check lives in one place (repo query) | Slightly harder to debug legitimate integration mistakes (wrong ID vs wrong account look identical) | Security wins; debugging cost is acceptable for UUID-based IDs that are never guessable by accident |
| **Per-endpoint choice** | Flexibility | Inconsistent behavior across the API; easy to leak existence by accident on new endpoints | Convention must be uniform to be trustworthy |

## Consequences

### Positive

- No existence oracle: enumerating UUIDs reveals nothing about other mayoristas' models
- Single enforcement point: the repository's `mayorista_id` filter — no separate authorization check that can be forgotten
- Uniform convention for all future ownership-scoped endpoints (pose-set-service, batch services, etc.)

### Negative

- Legitimate "wrong account" mistakes surface as confusing 404s instead of clear 403s
- API consumers cannot distinguish "deleted" from "never yours" — acceptable for this domain

### Risks

- **Developer confusion when testing cross-account scenarios**: Mitigation: this ADR documents the convention; story acceptance criteria pin the behavior with tests.

## Related

- **Stories**: 002-upload-pose-photo, 003-list-model-poses
- **Standards**: Should be added to api-conventions.md under "HTTP Status Codes" (403 vs 404 guidance)
- **Previous ADRs**: ADR-001 (separate auth contexts — same defense-in-depth philosophy)

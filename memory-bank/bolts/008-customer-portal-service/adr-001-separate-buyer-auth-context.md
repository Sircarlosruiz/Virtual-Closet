---
bolt: 008-customer-portal-service
created: 2026-05-28T18:00:00Z
status: accepted
superseded_by: null
---

# ADR-001: Separate Buyer Authentication Context

## Context

The Virtual Closet platform serves two distinct user types: mayoristas (wholesalers who manage catalogs) and buyers (customers who browse published catalogs). These user types have fundamentally different access patterns, security requirements, and session lifecycles. Mayoristas need full CRUD access to their catalogs and customer management, while buyers need read-only access to published catalogs from their associated mayorista.

The platform already has a mayorista authentication system using JWT tokens stored in an `access_token` cookie. The question is whether to extend this system to support buyers (unified auth with roles) or create a completely separate authentication context for buyers.

## Decision

Use completely separate authentication contexts for buyers and mayoristas:

- **Mayorista auth**: `access_token` cookie, path `/api`, JWT with `type: "mayorista"`
- **Buyer auth**: `buyer_session` cookie, path `/api/portal`, JWT with `type: "buyer_session"`

Each context has its own:
- Cookie name and path
- JWT structure and claims
- Dependency injection function (`get_current_mayorista` vs `get_current_buyer`)
- Database table (`mayorista` vs `customer`)

Buyer sessions cannot access mayorista endpoints, and mayorista sessions cannot access portal endpoints.

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Unified RBAC** (single `user` table with `role` field) | Single auth system, easier to manage, standard pattern | Over-engineered for two distinct user types with no overlap; requires complex permission checks on every endpoint; mayoristas and buyers have different data models (mayorista has business info, buyer has mayorista_id FK) | Rejected: Adds complexity without benefit — users never switch roles |
| **Shared JWT, different claims** (same cookie, `role` claim distinguishes) | Single cookie, simpler frontend | Risk of privilege escalation if role check is missed; cookie path restrictions don't apply; harder to enforce separation at middleware level | Rejected: Weaker security boundary, relies on correct role checks everywhere |
| **OAuth/OIDC provider** (Auth0, Cognito) | Industry standard, managed service, SSO capabilities | Adds external dependency, cost, latency; overkill for simple two-role system; existing mayorista auth already works | Rejected: Unnecessary complexity for current scale |

### Why Separate Contexts

1. **Security isolation**: Cookie path restrictions (`/api` vs `/api/portal`) provide defense-in-depth. Even if a buyer session token is compromised, it cannot access mayorista endpoints.

2. **Data model clarity**: Mayoristas and buyers have fundamentally different attributes. Mayoristas have `nombre_negocio`, `email`, `password_hash`. Buyers have `mayorista_id` (FK), `name`, `email`, `invitation_token_hash`. Forcing them into a single table with nullable fields creates confusion.

3. **Session lifecycle**: Mayorista sessions are long-lived (7 days, refreshable). Buyer sessions are tied to invitation/magic-link tokens and have different expiry semantics. Separate contexts allow independent evolution.

4. **No role switching**: A user is either a mayorista OR a buyer, never both in the same session. Unified RBAC adds complexity for a use case that doesn't exist.

5. **Simpler authorization**: Portal endpoints only check "is this a valid buyer session for this mayorista?" Mayorista endpoints only check "is this a valid mayorista session?" No need for complex permission matrices.

## Consequences

### Positive

- **Strong security boundary**: Cookie path restrictions enforce separation at the HTTP layer
- **Clear data model**: Each user type has its own table with appropriate fields
- **Independent evolution**: Can change buyer auth (e.g., add MFA) without affecting mayorista auth
- **Simpler authorization logic**: No role checks needed — context determines access
- **Easier testing**: Can test buyer and mayorista flows independently

### Negative

- **Code duplication**: Two separate auth systems means some duplicated logic (JWT encoding/decoding, cookie handling)
- **Two dependency functions**: Need to maintain `get_current_mayorista` and `get_current_buyer`
- **Potential confusion**: Developers must understand which context applies to which endpoints

### Risks

- **Risk**: Developer accidentally uses wrong dependency function (e.g., `get_current_mayorista` on portal endpoint)
  - **Mitigation**: Cookie path restrictions prevent cross-context access even if wrong dependency is used. Code review checklist includes "verify correct auth dependency."

- **Risk**: Future requirement for users to be both mayorista and buyer
  - **Mitigation**: Unlikely given business model (mayoristas are wholesalers, buyers are their customers). If needed, can add a bridge table later without refactoring auth.

## Related

- **Stories**: 001-register-customer, 002-buyer-portal-auth, 003-browse-published-catalogs
- **Standards**: None (implementation-specific decision)
- **Previous ADRs**: None (first ADR in project)

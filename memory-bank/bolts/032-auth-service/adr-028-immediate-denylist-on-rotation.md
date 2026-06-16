---
bolt: 032-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-028: Immediate Denylist on Token Rotation

## Context

Token rotation issues a new refresh token each time the `/auth/refresh` endpoint is called, while revoking the old one. If the old token's JTI is not immediately added to the Redis denylist, a race condition could allow concurrent refresh attempts (e.g., from a buggy frontend making duplicate requests) to both succeed, resulting in multiple active refresh tokens for the same session. This undermines the rotation pattern's security benefit of detecting token theft.

**Forces**:
- Prevent concurrent refresh attempts from both succeeding
- Maintain atomic rotation: old token revoked before new token issued
- Handle race conditions gracefully (first wins, second fails)
- Minimize latency impact on refresh endpoint

## Decision

During token rotation, the old refresh token's JTI is added to the Redis denylist using `SETNX` (atomic set-if-not-exists) with TTL equal to the remaining token lifetime, *before* the new refresh token is issued. If the SETNX succeeds (key did not exist), rotation proceeds. If SETNX fails (key already exists), the request is rejected with 401 — this indicates a concurrent refresh already processed this token. The sequence is: (1) validate old token, (2) SETNX denylist entry, (3) if SETNX succeeded, create new tokens, (4) return new tokens.

## Rationale

SETNX provides atomic check-and-set in a single Redis operation, eliminating the race window between checking the denylist and adding the entry. By adding to the denylist *before* issuing new tokens, we ensure that any concurrent request with the same old token will find it already denied. This pattern is used by OAuth 2.0 refresh token rotation implementations (RFC 6819, OWASP guidelines).

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Check denylist, then add after issuing new token** | Simpler code | Race window between check and add; concurrent requests could both pass | Creates security gap |
| **Database-level unique constraint on JTI** | Durable, atomic | Higher latency, requires DB round-trip for each refresh | Redis is faster and already the denylist |
| **Optimistic locking with version field** | Detects concurrent modifications | Requires additional field, complex retry logic | SETNX is simpler and atomic |
| **Single-use refresh tokens (no rotation)** | Simpler, no race conditions | User must re-login on every refresh | Poor UX for 7-day session requirement |

## Consequences

### Positive

- Atomic rotation prevents concurrent refresh race conditions
- First refresh succeeds; concurrent duplicates fail with 401
- SETNX is a single Redis operation (~0.1ms latency)
- Consistent with OAuth 2.0 best practices

### Negative

- Frontend must handle 401 on concurrent refresh (should retry with new token or redirect to login)
- Requires careful ordering: denylist before new token issuance

### Risks

- **Redis SETNX failure**: If Redis command fails mid-operation, rotation state is inconsistent. Mitigation: wrap in try/except, return 503 on Redis error.
- **Frontend retry storms**: Duplicate refresh requests from buggy frontend cause 401 errors. Mitigation: frontend should debounce refresh calls and handle 401 gracefully.

## Related

- **Stories**: 009-jwt-session-management
- **Standards**: Should be documented in API client guidelines for refresh token handling
- **Previous ADRs**: ADR-016 (Redis denylist), ADR-025 (challenge token single-use via SETNX)

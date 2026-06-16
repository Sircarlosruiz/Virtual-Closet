---
bolt: 032-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-027: Fail-Closed on Redis Outage for Token Refresh

## Context

The refresh token validation flow depends on the Redis denylist to check whether a token has been revoked (logged out, rotated, or password reset). If Redis is unavailable during a refresh request, the system must decide whether to allow the refresh (fail-open) or reject it (fail-closed). Allowing a refresh without checking the denylist could permit a revoked token to obtain a new access token, undermining the security model.

**Forces**:
- Security: revoked tokens must not be able to refresh
- Availability: users should not be locked out due to Redis outage
- Operational complexity: monitoring and alerting requirements
- User experience: 503 error vs. silent security degradation

## Decision

When Redis is unavailable during a token refresh request, the system returns HTTP 503 (Service Unavailable) with the message "Session service temporarily unavailable." This is a fail-closed approach: it is safer to temporarily block legitimate refreshes than to allow potentially revoked tokens to obtain new access tokens. The existing 15-minute access token window provides a grace period — users with valid access tokens can continue using the API until their token expires.

## Rationale

Fail-closed is the correct security posture for authentication systems. Allowing a refresh without checking the denylist creates a window where revoked tokens (from logout, password reset, or admin action) could be refreshed, defeating the purpose of revocation. The 15-minute access token TTL limits the impact: users are not immediately locked out, and the outage is visible (503) rather than silently degrading security.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Fail-open (allow refresh without Redis check)** | Users not interrupted during Redis outage | Revoked tokens can refresh, defeating revocation | Unacceptable security risk |
| **In-memory denylist cache** | Works during Redis outage | Stale data, memory growth, not shared across workers | Adds complexity, still inconsistent |
| **PostgreSQL denylist fallback** | Durable, available if Redis is down | Higher latency (~10ms vs ~0.1ms), defeats Redis performance benefit | Redis is the primary design; PG fallback adds complexity |
| **Graceful degradation with logging** | Users not interrupted | Silent security degradation, hard to detect | Violates security-first principle |

## Consequences

### Positive

- Revoked tokens cannot be refreshed during Redis outage
- Security posture is maintained under failure conditions
- Outage is visible (503) — triggers monitoring alerts
- Existing access tokens provide 15-minute grace period

### Negative

- Users cannot refresh during Redis outage (must re-login after access token expires)
- 503 errors may increase support tickets during outages
- Requires Redis monitoring and alerting to minimize outage duration

### Risks

- **Extended Redis outage**: Users forced to re-login after 15 minutes. Mitigation: monitor Redis health, set up automatic failover or Redis Sentinel.
- **Cascading failures**: 503 on refresh may cause frontend retry storms. Mitigation: frontend should implement exponential backoff and show user-friendly "session expired" message.

## Related

- **Stories**: 009-jwt-session-management
- **Standards**: Should be documented in operational runbook for Redis outage procedures
- **Previous ADRs**: ADR-016 (Redis denylist for session invalidation), ADR-023 (Redis for ephemeral auth state)

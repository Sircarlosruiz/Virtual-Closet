---
stage: adr
bolt: 029-tenant-account-service
created: 2026-06-09T19:40:00Z
---

# ADR-016: Redis Denylist for Admin Session Invalidation

## Context

When an admin is revoked from a tenant, their access must be terminated. The platform uses short-lived JWT access tokens (15-minute TTL) and longer-lived refresh tokens. Revoking the refresh tokens in the database is straightforward, but active access tokens remain valid until they expire naturally (up to 15 minutes).

For immediate session invalidation, a denylist mechanism is needed to reject token refresh attempts from revoked admins.

## Decision

Use Redis as a token JTI (JWT ID) denylist for session invalidation on admin revocation.

When an admin is revoked:
1. All active refresh token JTIs for that user are fetched from the database
2. Each JTI is added to Redis with a key `denylist:{jti}` and value `"1"`
3. The Redis key TTL is set to match the remaining TTL of the original refresh token
4. On token refresh, the service checks Redis for the JTI — if present, the refresh is rejected

## Rationale

- **PostgreSQL alternative**: Storing revoked JTIs in PostgreSQL would add write load to the database for every revocation and require periodic cleanup of expired entries. PostgreSQL is not optimized for high-frequency key-value lookups with automatic expiration.
- **Redis advantages**: Native TTL support, O(1) key lookup, sub-millisecond latency, automatic cleanup of expired entries. The denylist check adds < 1ms to the token refresh flow.
- **Scope**: Redis is introduced solely for session management. It does not replace PostgreSQL for any persistent data.
- **Deployment impact**: Redis must be added to Docker Compose (dev) and k3s (prod) configurations.

## Consequences

- **Positive**: Immediate session invalidation capability; minimal latency impact on token refresh; automatic cleanup via Redis TTL
- **Negative**: New infrastructure dependency (Redis) must be provisioned and monitored; adds complexity to Docker Compose and k3s deployment
- **Trade-off accepted**: The 15-minute access token window remains — access tokens cannot be revoked immediately, only refresh tokens. This is an accepted risk given the short TTL.

## Implementation Notes

- Redis connection should use the existing backend connection pool pattern
- Key format: `denylist:{jti}` — namespaced to avoid collisions with other Redis usage
- The denylist check should be a non-blocking operation — if Redis is unavailable, the refresh should proceed (fail-open) to avoid locking out valid users

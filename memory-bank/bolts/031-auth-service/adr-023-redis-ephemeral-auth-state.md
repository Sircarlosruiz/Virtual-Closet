---
bolt: 031-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-023: Redis as Primary Store for Ephemeral Auth State

## Context

The 2FA system requires fast, ephemeral storage for several time-sensitive values: TOTP replay protection (prevent same code reuse within 30s window), SMS OTP rate limiting (max 3 sends per 10 minutes), active SMS OTP hashes (5-min TTL), and challenge token single-use tracking. The project already uses Redis for the refresh token denylist (ADR-016), but this bolt extends Redis usage to cover additional auth-critical ephemeral state.

**Forces**:
- Ephemeral values have short TTLs (30s–10min) — PostgreSQL is overkill and adds unnecessary I/O
- Redis is already a required dependency (refresh token denylist)
- Redis unavailability should not block core authentication flows
- Rate limiting and replay protection require atomic operations

## Decision

Use Redis as the primary store for all ephemeral auth state with the following key patterns:
- `totp:used:{user_id}:{totp_code}` — 90s TTL, replay protection
- `sms:rate:{user_id}` — 600s TTL, rate limit counter (INCR + EXPIRE)
- `sms:otp:{user_id}` — 300s TTL, active SMS OTP hash
- `challenge:consumed:{jti}` — 300s TTL, single-use challenge token tracking

All Redis operations use the existing shared Redis connection. If Redis is unavailable, the system degrades gracefully: replay protection and rate limiting are skipped, but core 2FA validation proceeds (the user can still authenticate).

## Rationale

Redis is the natural fit for ephemeral state with automatic TTL expiration. The project already depends on Redis for the refresh token denylist, so there is no new infrastructure cost. Redis atomic operations (INCR, SETNX, EXPIRE) handle concurrency correctly without database transactions. Graceful degradation ensures authentication is not blocked by Redis outages.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **PostgreSQL for ephemeral state** | Durable, already available, transactional | Unnecessary I/O for values with 30s–10min TTL, requires cleanup jobs, higher latency | Redis TTL is simpler and faster |
| **In-memory dict (process-local)** | Zero latency, no external dependency | Not shared across workers, lost on restart, no TTL management | Multi-worker deployment requires shared state |
| **PostgreSQL + scheduled cleanup** | Durable, no new dependency | Cleanup jobs add complexity, stale rows accumulate | Redis automatic expiration is simpler |

## Consequences

### Positive

- Sub-millisecond reads/writes for ephemeral state
- Automatic expiration via Redis TTL — no cleanup jobs needed
- Atomic operations (INCR, SETNX) handle concurrency correctly
- Shared Redis connection with existing denylist — no new infrastructure

### Negative

- Redis outage disables replay protection and rate limiting (security degradation)
- Redis memory usage grows with active users (mitigated by short TTLs)
- Adds operational dependency — Redis must be monitored

### Risks

- **Redis outage**: Replay protection and rate limiting skip silently. Mitigation: monitor Redis health, alert on connection failures. Core authentication still functions.
- **Memory exhaustion**: Unbounded key growth if TTLs fail. Mitigation: configure Redis maxmemory with allkeys-lru eviction policy.
- **Race conditions**: Multiple workers checking rate limit simultaneously. Mitigation: use Redis atomic INCR + EXPIRE in a single pipeline.

## Related

- **Stories**: 005-totp-2fa-setup-and-challenge, 006-sms-otp-2fa-fallback
- **Standards**: Redis key naming convention should be documented
- **Previous ADRs**: ADR-016 (Redis denylist for session invalidation — extends Redis auth usage)

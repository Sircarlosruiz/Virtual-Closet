---
bolt: 031-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-025: Challenge Token Single-Use via Redis Tracking

## Context

ADR-018 defined the `challenge_token` pattern: a short-lived (5-min) HS256-signed token returned after credential validation, which must be presented to 2FA or OAuth exchange endpoints before JWT issuance. However, ADR-018 did not specify how to enforce single-use — without it, a challenge_token could be replayed to obtain multiple JWT sessions, undermining the security model.

**Forces**:
- Challenge tokens must be consumed exactly once
- Replay must be detected and rejected within the 5-minute validity window
- The mechanism must be fast (adds latency to every 2FA/OAuth request)
- Must work across multiple FastAPI workers

## Decision

Track challenge token consumption in Redis using the key pattern `challenge:consumed:{jti}` with a 300-second (5-minute) TTL matching the token's expiry. When a challenge token is successfully used (2FA validated or OAuth exchange completed), the `ChallengeTokenService` sets this Redis key via SETNX (atomic set-if-not-exists). On subsequent attempts with the same token, the service checks for the key's existence and rejects the request if found.

The Redis check is performed after JWT signature validation and expiry check, so an invalid or expired token is rejected before the Redis lookup.

## Rationale

Redis SETNX provides atomic single-use enforcement across all workers. The 5-minute TTL ensures the key expires naturally, preventing unbounded memory growth. This approach is consistent with the existing Redis usage for refresh token denylist (ADR-016) and extends it to the challenge token lifecycle.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Database flag on challenge token** | Durable, auditable | Requires DB write on every 2FA request, higher latency, cleanup needed | Redis is faster and auto-expires |
| **In-memory set (process-local)** | Zero latency | Not shared across workers, lost on restart | Multi-worker deployment requires shared state |
| **Token embedding (embed "used" flag in JWT)** | Stateless, no storage needed | JWT is immutable — cannot mark as used after issuance | Fundamentally incompatible with JWT design |
| **Shorter token TTL (30s)** | Reduces replay window | May expire during legitimate 2FA setup (user scanning QR code) | 5 minutes is the minimum UX-acceptable window |

## Consequences

### Positive

- Atomic single-use enforcement across all workers
- Automatic cleanup via Redis TTL — no maintenance needed
- Adds ~1ms latency per 2FA/OAuth request (negligible)
- Consistent with existing Redis auth patterns (ADR-016, ADR-023)

### Negative

- Redis outage disables single-use enforcement (challenge tokens become reusable within 5-min window)
- Adds another Redis key pattern to manage and monitor

### Risks

- **Redis outage**: Challenge tokens become replayable for up to 5 minutes. Mitigation: monitor Redis health. The window is short, and replay requires the attacker to have the challenge_token (which is already a post-credential-validation state).
- **Clock skew**: Token expiry and Redis TTL may drift slightly. Mitigation: use the same NTP-synced servers for both JWT expiry and Redis TTL.

## Related

- **Stories**: 005-totp-2fa-setup-and-challenge, 006-sms-otp-2fa-fallback, 007-google-oauth-login
- **Standards**: Challenge token lifecycle documentation
- **Previous ADRs**: ADR-018 (challenge token pattern — this implements the single-use enforcement)

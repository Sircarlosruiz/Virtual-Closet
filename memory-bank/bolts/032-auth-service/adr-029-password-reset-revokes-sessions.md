---
bolt: 032-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-029: Password Reset Revokes All Active Sessions

## Context

When a user resets their password, all existing sessions (access tokens and refresh tokens) should be invalidated to prevent unauthorized access from potentially compromised sessions. However, access tokens are stateless JWTs with a 15-minute TTL — they cannot be revoked individually without introducing a denylist for access tokens (which would negate the benefit of stateless verification). The question is: what level of session invalidation is sufficient and practical?

**Forces**:
- Prevent access from sessions created before password reset
- Access tokens are stateless — cannot be individually revoked without a denylist
- 15-minute access token TTL limits the window of continued access
- NIST SP 800-63B recommends session invalidation on credential change
- User experience: should not require immediate re-login if password reset was legitimate

## Decision

On successful password reset, all active refresh tokens for the user are revoked in PostgreSQL (marked `revoked=true`) and their JTIs are added to the Redis denylist with TTL matching remaining lifetime. This prevents any new access tokens from being issued. Existing access tokens remain valid until their 15-minute expiry — this is an accepted risk consistent with NIST SP 800-63B guidance, which states that the access token window is an acceptable trade-off for the simplicity of stateless verification. No access token denylist is introduced.

## Rationale

Revoking refresh tokens is sufficient to prevent continued access beyond the 15-minute access token window. Adding an access token denylist would require checking every API request against Redis, negating the performance benefit of stateless JWT verification. The 15-minute window is short enough that the risk is acceptable for this application. NIST SP 800-63B Section 7.1 recommends revoking sessions on credential change but acknowledges that short-lived tokens provide adequate protection.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Access token denylist** | Immediate revocation of all sessions | Adds Redis check to every API request, negates stateless JWT benefit | Performance cost outweighs 15-minute risk reduction |
| **Version claim in JWT** | Increment version on password reset; old tokens fail verification | Requires DB lookup on every request to check current version | Adds latency to every API call |
| **Shorter access token TTL (5 min)** | Reduces window of continued access | More frequent refresh calls, higher Redis load | 15 minutes is standard; 5 minutes is aggressive |
| **Force re-login on password reset** | Clear UX, immediate security | User must re-enter credentials immediately after reset | Poor UX; user just proved identity via reset token |

## Consequences

### Positive

- Refresh tokens immediately revoked — no new access tokens can be issued
- No access token denylist needed — maintains stateless verification performance
- Consistent with NIST SP 800-63B recommendations
- Simple implementation: iterate and revoke in DB + add to Redis

### Negative

- 15-minute window where old access tokens remain valid
- User may see "session expired" on next API call after 15 minutes

### Risks

- **Attacker with valid access token**: Can continue using API for up to 15 minutes after password reset. Mitigation: 15-minute window is short; sensitive operations should require re-authentication (e.g., password confirmation for account changes).
- **Multiple devices**: All devices lose refresh tokens simultaneously. Mitigation: this is the desired behavior — password change should invalidate all sessions.

## Related

- **Stories**: 008-password-reset, 009-jwt-session-management
- **Standards**: Should be documented in security policy for credential change procedures
- **Previous ADRs**: ADR-016 (Redis denylist), ADR-027 (fail-closed on Redis outage)

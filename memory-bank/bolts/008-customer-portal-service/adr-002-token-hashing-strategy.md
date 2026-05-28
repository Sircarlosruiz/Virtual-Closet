---
bolt: 008-customer-portal-service
created: 2026-05-28T18:05:00Z
status: accepted
superseded_by: null
---

# ADR-002: Token Hashing Strategy (bcrypt)

## Context

The customer portal uses invitation tokens (7-day TTL) and magic-link tokens (15-minute TTL) to authenticate buyers. These tokens are sent via email as URL parameters and must be validated server-side. The question is how to store these tokens securely in the database.

Tokens are sensitive credentials: if leaked, they grant access to the buyer portal. The storage strategy must balance security (protecting against database breaches) with performance (token validation happens on every auth attempt).

## Decision

Hash invitation and magic-link tokens with **bcrypt** before storage:

- Generate random token (32 bytes, base64-encoded)
- Hash with bcrypt (cost factor 12, default)
- Store only the hash in `customer.invitation_token_hash`
- Send plaintext token in email URL
- Validate by hashing provided token and comparing to stored hash

Never persist plaintext tokens in the database, logs, or error messages.

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Plaintext storage** | Fastest validation (direct string comparison), simplest implementation | If database is breached, all tokens are exposed; violates security best practices; compliance issues (GDPR, PCI-DSS) | Rejected: Unacceptable security risk |
| **SHA-256 with salt** | Fast hashing, widely supported | Not designed for password/token hashing; vulnerable to GPU/ASIC attacks; requires managing salt separately | Rejected: bcrypt is purpose-built for this use case |
| **Argon2id** | Modern, memory-hard, resistant to GPU attacks; winner of Password Hashing Competition | Newer, less battle-tested than bcrypt; higher memory usage; not available in all environments | Rejected: bcrypt is sufficient for low-frequency auth operations and has broader support |
| **scrypt** | Memory-hard, resistant to hardware attacks | Less common than bcrypt; some implementations have bugs; higher memory usage | Rejected: bcrypt is simpler and well-supported |
| **HMAC with server secret** | Fast, allows token revocation by rotating secret | If secret is compromised, all tokens can be forged; requires managing secret rotation | Rejected: Adds complexity without clear benefit for short-lived tokens |

### Why bcrypt

1. **Purpose-built for credentials**: bcrypt is designed for hashing passwords and tokens with intentional slowness to resist brute-force attacks.

2. **Built-in salt**: bcrypt generates and stores a random salt with each hash, eliminating salt management complexity.

3. **Acceptable performance**: Token validation is infrequent (once per invitation/magic-link use). bcrypt's intentional slowness (100-300ms per hash) is acceptable for this use case.

4. **Battle-tested**: bcrypt has been in use since 1999 and is widely supported across languages and frameworks.

5. **Cost factor tunability**: Can increase cost factor (currently 12) in the future if hardware improves, without changing the overall approach.

6. **Compliance**: Meets security best practices and compliance requirements (OWASP, NIST) for credential storage.

### Performance Considerations

- **Hashing on registration**: ~200ms per hash (one-time cost when customer is created)
- **Validation on auth**: ~200ms per validation (infrequent — happens once per invitation/magic-link use)
- **Impact**: Negligible for portal use case (low-frequency auth operations)

If performance becomes an issue (e.g., high-volume magic-link requests), can:
- Reduce cost factor to 10 (still secure, ~50ms per hash)
- Add rate limiting to auth endpoints
- Cache validated sessions (already done via buyer_session cookie)

## Consequences

### Positive

- **Security**: Database breach does not expose plaintext tokens
- **Compliance**: Meets OWASP and NIST guidelines for credential storage
- **Simplicity**: bcrypt handles salt generation and storage automatically
- **Flexibility**: Can increase cost factor in the future without schema changes

### Negative

- **Performance overhead**: ~200ms per hash/validation operation
- **No token lookup by value**: Cannot query "which customer has this token?" (must fetch customer by email/ID first, then validate hash)

### Risks

- **Risk**: Developer accidentally logs plaintext token
  - **Mitigation**: Code review checklist includes "verify tokens are never logged." Add linting rule to flag `console.log(token)` patterns.

- **Risk**: Performance becomes unacceptable at scale
  - **Mitigation**: Monitor auth endpoint latency. If >500ms p95, reduce bcrypt cost factor or add caching layer.

- **Risk**: bcrypt becomes obsolete (e.g., quantum computing breakthrough)
  - **Mitigation**: Monitor cryptographic best practices. If bcrypt is deprecated, can migrate to argon2id by rehashing tokens on next validation (requires users to re-authenticate).

## Related

- **Stories**: 001-register-customer, 002-buyer-portal-auth
- **Standards**: None (implementation-specific decision)
- **Previous ADRs**: ADR-001 (Separate Buyer Authentication Context)

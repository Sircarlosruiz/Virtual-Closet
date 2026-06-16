---
bolt: 032-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-026: RS256 Asymmetric Signing for Access Tokens

## Context

The current authentication system uses HS256 (symmetric HMAC) for JWT signing, requiring the same secret key for both signing and verification. This means any service that can verify tokens can also forge them. The tech-stack specifies RS256 asymmetric keys with a public key endpoint at `/.well-known/jwks.json`, enabling downstream services to verify tokens without access to the signing secret.

**Forces**:
- Access tokens must be verifiable by multiple services without sharing secrets
- Public key must be accessible for downstream service integration
- Private key must be protected as a high-value secret
- Key rotation should be possible without disrupting active sessions

## Decision

Use RS256 (RSA Signature with SHA-256) for access token signing. The private key is stored as the `JWT_PRIVATE_KEY` environment variable (PEM format, RSA 2048-bit minimum). The public key is derived from the private key at startup and served at `GET /.well-known/jwks.json` in standard JWKS format. JWT claims include `{ sub, tenant_id, role, iat, exp, jti }`. The `kid` (key ID) header identifies which key was used for signing, supporting future key rotation.

## Rationale

RS256 provides asymmetric cryptography: the private key signs tokens, and the public key verifies them. This enables secure token distribution — downstream services can verify tokens using the public key without ever having access to the signing secret. The JWKS standard is widely adopted and supported by JWT libraries.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **HS256 (current)** | Simple, fast, single key | Secret shared with all verifiers; any verifier can forge tokens | Insecure for multi-service architecture |
| **ES256 (ECDSA)** | Smaller signatures, faster verification | Less widely supported, key management more complex | RS256 is more mature and widely adopted |
| **EdDSA (Ed25519)** | Fastest, smallest signatures | Limited library support in Python ecosystem | RS256 has broader ecosystem support |

## Consequences

### Positive

- Downstream services verify tokens without access to signing secret
- Public key endpoint enables third-party integration
- `kid` header supports future key rotation
- Industry standard — widely understood and supported

### Negative

- RS256 signing is slower than HS256 (~0.5ms vs ~0.05ms) — negligible at current scale
- Key management is more complex (PEM format, environment variable)
- Larger token size due to RSA signature

### Risks

- **Private key exposure**: If leaked, attacker can forge tokens. Mitigation: treat as highest-priority secret, rotate immediately if compromised.
- **Key rotation complexity**: Requires serving both old and new public keys during transition. Mitigation: JWKS supports multiple keys.

## Related

- **Stories**: 009-jwt-session-management
- **Standards**: Should be added to tech-stack.md as the JWT signing algorithm
- **Previous ADRs**: ADR-018 (challenge token pattern — challenge tokens remain HS256)

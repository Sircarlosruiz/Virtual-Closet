---
bolt: 031-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
superseded_by: null
---

# ADR-022: Fernet Symmetric Encryption for Sensitive Auth Fields

## Context

The 2FA system needs to store TOTP secrets (32-char base32) and phone numbers (E.164 format) in PostgreSQL. These are sensitive values that must not be readable in the database if it is compromised, but must be decryptable by the application at runtime for validation and SMS delivery. The project has no existing symmetric encryption standard — previous sensitive data (passwords, tokens) uses one-way hashing (bcrypt).

**Forces**:
- TOTP secrets must be decryptable to validate user-submitted codes
- Phone numbers must be decryptable to send SMS via Twilio
- Database backups and replicas may be accessible to different personnel
- Encryption key must be managed separately from the database

## Decision

Use Fernet symmetric encryption (from the `cryptography` library) for TOTP secrets and phone numbers stored in `two_factor_configs`. The encryption key is provided via the `TWO_FACTOR_ENCRYPTION_KEY` environment variable (URL-safe base64-encoded 32-byte key). Encryption and decryption happen at the repository layer — services work with plaintext values; repositories encrypt on write and decrypt on read.

## Rationale

Fernet provides authenticated encryption (AES-128-CBC + HMAC-SHA256), ensuring both confidentiality and integrity. It is a well-established standard, included in the widely-used `cryptography` library, and requires no external service. The key is a single 32-byte value, simple to manage via environment variables or secrets managers.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Plaintext storage** | Simple, no key management | Data exposed in DB backups, violates security best practices | Unacceptable for secrets and PII |
| **Application-level hashing** | One-way, no decryption needed | TOTP validation requires the secret; phone numbers must be dialable | Cannot work for values that must be recovered |
| **AWS KMS / HashiCorp Vault** | Centralized key management, rotation | Adds infrastructure complexity, external dependency | Overkill for current scale; can migrate later |
| **PostgreSQL pgcrypto** | Encryption at DB level, no app key management | Ties encryption to PostgreSQL, harder to rotate keys, less portable | Fernet is simpler and database-agnostic |

## Consequences

### Positive

- Sensitive fields encrypted at rest with authenticated encryption
- Single key to manage, easy to rotate (re-encrypt all values)
- No external service dependency — works in Docker Compose and k3s
- Decryption failure is detectable (Fernet validates HMAC)

### Negative

- Key management is the operator's responsibility — lost key = lost data
- Encryption/decryption adds ~1ms per operation (negligible)
- Encrypted values are ~1.5× larger than plaintext (base64 + IV + HMAC)

### Risks

- **Key leakage**: If `TWO_FACTOR_ENCRYPTION_KEY` is exposed, all encrypted values are compromised. Mitigation: treat key as a secret, never log it, use environment variable injection in deployment.
- **Key rotation**: Requires re-encrypting all existing values. Mitigation: support dual-key decryption during transition period (try new key, fall back to old key).

## Related

- **Stories**: 005-totp-2fa-setup-and-challenge, 006-sms-otp-2fa-fallback
- **Standards**: Should be added to coding-standards.md as the project's symmetric encryption pattern
- **Previous ADRs**: ADR-002 (token hashing with bcrypt — complementary, not conflicting)

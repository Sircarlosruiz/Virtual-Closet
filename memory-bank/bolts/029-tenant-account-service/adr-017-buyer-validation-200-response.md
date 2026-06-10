---
stage: adr
bolt: 029-tenant-account-service
created: 2026-06-09T19:40:00Z
---

# ADR-017: Buyer Link Validation Returns 200 on Invalid Tokens

## Context

The buyer catalog access link validation endpoint (`POST /buyer-links/validate`) is a public endpoint that verifies JWT tokens issued to buyers. Unlike authenticated endpoints that return 401/403 for invalid credentials, this endpoint serves unauthenticated buyers who have no session to refresh.

## Decision

The `POST /buyer-links/validate` endpoint always returns HTTP 200, regardless of token validity. Invalid or expired tokens return `{ valid: false, reason: "..." }` in the response body.

Valid token response:
```json
{ "valid": true, "tenant_id": "...", "catalog_ids": ["..."] }
```

Invalid token response:
```json
{ "valid": false, "reason": "link_expired" | "invalid_token" }
```

## Rationale

- **No session to refresh**: Buyers have no login session. Returning 401 would imply the buyer should authenticate, which is not applicable.
- **Security**: Returning different HTTP status codes for different failure modes (malformed token vs. expired token vs. wrong signature) could leak information to attackers probing the endpoint. A uniform 200 response with a reason code in the body provides consistent behavior.
- **Frontend simplicity**: The frontend can handle a single response shape (`valid: boolean`) without special HTTP error handling.
- **Consistency**: This pattern is common in public token validation endpoints (e.g., email verification links, password reset tokens).

## Consequences

- **Positive**: Consistent response shape; no HTTP error handling needed on frontend; no information leakage via status codes
- **Negative**: API consumers must always check the `valid` field in the response body — cannot rely on HTTP status codes
- **Monitoring**: Health checks and error monitoring must be configured to not flag 200 responses with `valid: false` as errors

## Implementation Notes

- The `reason` field should use stable string constants: `"link_expired"`, `"invalid_token"`
- Logging should still record invalid token attempts at `warn` level for security monitoring
- Rate limiting should apply to this endpoint to prevent brute-force token probing

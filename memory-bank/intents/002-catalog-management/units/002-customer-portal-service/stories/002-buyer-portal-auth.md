---
id: 002-buyer-portal-auth
unit: 002-customer-portal-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 008-customer-portal-service
implemented: true
---

# Story: 002-buyer-portal-auth

## User Story

**As a** registered buyer
**I want** to access the buyer portal via my invitation link (or request a new link)
**So that** I can browse the catalogs shared with me

## Acceptance Criteria

- [ ] **Given** I click a valid invitation link `GET /api/portal/auth?token=<token>`, **When** processed, **Then** the token is validated, a buyer session cookie is issued, and I am redirected to the portal
- [ ] **Given** the token is expired (> 7 days old), **When** I use it, **Then** I receive 401 with "Link expired. Request a new one."
- [ ] **Given** the token has already been used and reuse is detected (optional: single-use tokens), **When** I use it, **Then** redirect proceeds (tokens are multi-use within TTL — not single-use in MVP)
- [ ] **Given** I am logged in as a buyer and request `POST /api/portal/magic-link` with `{ email }`, **When** my email matches a registered customer, **Then** a new magic-link email is sent with a fresh 15-minute token
- [ ] **Given** the email in magic-link request does not match any customer, **When** processed, **Then** I receive 200 (no enumeration — always respond 200)

## Technical Notes

- Buyer session cookie: HttpOnly, SameSite=Strict, 7-day TTL; separate from mayorista JWT
- Magic-link token: short-lived JWT (15 min), delivered via email
- Invitation link token: 7-day JWT — same validation path as magic-link
- Session cookie must NOT grant mayorista-level access to any admin endpoint

## Dependencies

### Requires
- 001-register-customer (customer must exist)

### Enables
- 003-browse-published-catalogs (needs authenticated buyer session)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Token tampered (invalid signature) | 401 invalid token |
| Buyer account for a mayorista who deleted all catalogs | Auth succeeds; portal shows empty catalog list |
| Magic-link request with unregistered email | 200 (no enumeration) |

## Out of Scope

- MFA for buyer portal
- OAuth / social login for buyers

---
id: 001-register-customer
unit: 002-customer-portal-service
intent: 002-catalog-management
status: complete
priority: must
created: 2026-05-28T00:00:00.000Z
assigned_bolt: 008-customer-portal-service
implemented: true
---

# Story: 001-register-customer

## User Story

**As a** mayorista
**I want** to register a buyer/customer by name and email
**So that** they receive an invitation to access my catalogs in the buyer portal

## Acceptance Criteria

- [ ] **Given** I am authenticated, **When** I POST `/api/customers` with `{ name: "Ana López", email: "ana@buyer.com" }`, **Then** a customer record is created with `status: invited`, and I receive `{ customer_id, name, email, status }`
- [ ] **Given** the customer is created, **When** the system processes the request, **Then** an invitation email is sent to `ana@buyer.com` with a signed access link (valid 7 days)
- [ ] **Given** I submit an email already registered under my account, **When** processed, **Then** I receive 409 with "Customer with this email already exists"
- [ ] **Given** I submit an invalid email format, **When** processed, **Then** I receive 400
- [ ] **Given** I am NOT authenticated, **When** I POST `/api/customers`, **Then** I receive 401

## Technical Notes

- Invitation token: signed JWT with `{ customer_id, mayorista_id }`, 7-day TTL
- Token stored as bcrypt hash in DB — plaintext only in the email link
- Email is unique per mayorista (not globally) — same email can be registered by different mayoristas
- Email sending is non-blocking (async task or fire-and-forget) — registration returns 201 immediately

## Dependencies

### Requires
- Platform JWT auth middleware (pre-existing)

### Enables
- 002-buyer-portal-auth (customer needs to exist to authenticate)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `name` is empty | 400 validation error |
| Email registered for a different mayorista | Allowed (different scope) |
| Re-registering same email for same mayorista | 409 conflict |

## Out of Scope

- Listing or managing registered customers (separate story if needed)
- Revoking customer access

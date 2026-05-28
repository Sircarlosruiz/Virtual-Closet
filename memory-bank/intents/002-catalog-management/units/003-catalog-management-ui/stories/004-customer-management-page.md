---
id: 004-customer-management-page
unit: 003-catalog-management-ui
intent: 002-catalog-management
status: completed
priority: must
created: 2026-05-28T00:00:00Z
assigned_bolt: 010-catalog-management-ui
implemented: true
completed: 2026-05-28T22:30:00Z
---

# Story: 004-customer-management-page

## User Story

**As a** mayorista
**I want** to register new buyers and view my registered customers
**So that** I can manage who has access to my buyer portal

## Acceptance Criteria

- [x] **Given** I navigate to the Customers section, **When** the page loads, **Then** I see a list of my registered customers with: name, email, and status (Invited / Active)
- [x] **Given** I have no customers, **When** the page loads, **Then** I see an empty state with "Register your first customer" CTA
- [x] **Given** I click "Register Customer", **When** a form appears, **Then** I can enter name and email, submit, and see the new customer appear with "Invited" status
- [x] **Given** registration succeeds, **When** I check, **Then** a confirmation message confirms an invitation email has been sent

## Technical Notes

- `GET /api/customers` — list customers for authenticated mayorista (not in requirements but implied; may need to add FR or handle in bolt)
- `POST /api/customers` → 201 → append to list
- Status badge: "Invited" (grey) for never-logged-in, "Active" (green) for customers who have authenticated at least once

## Dependencies

### Requires
- 001-register-customer API

### Enables
- 005-buyer-portal-page (customers must be registered to access portal)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Duplicate email submission | Show API 409 as form error "This email is already registered" |
| Email delivery failure (non-blocking) | Registration still succeeds; show warning "Customer registered but invitation email may be delayed" |

## Out of Scope

- Revoking customer access
- Resending invitation from this UI

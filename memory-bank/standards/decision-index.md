---
last_updated: 2026-05-28T18:05:00Z
total_decisions: 2
---

# Decision Index

This index tracks all Architecture Decision Records (ADRs) created during Construction bolts.
Use this to find relevant prior decisions when working on related features.

## How to Use

**For Agents**: Scan the "Read when" fields below to identify decisions relevant to your current task. Before implementing new features, check if existing ADRs constrain or guide your approach. Load the full ADR for matching entries.

**For Humans**: Browse decisions chronologically or search for keywords. Each entry links to the full ADR with complete context, alternatives considered, and consequences.

---

## Decisions

<!-- Entries are appended below in reverse chronological order (newest first) -->

### ADR-002: Token Hashing Strategy (bcrypt)
- **Status**: accepted
- **Date**: 2026-05-28
- **Bolt**: 008-customer-portal-service (002-customer-portal-service)
- **Path**: `bolts/008-customer-portal-service/adr-002-token-hashing-strategy.md`
- **Summary**: The customer portal uses invitation and magic-link tokens to authenticate buyers. Hash tokens with bcrypt before storage, never persist plaintext.
- **Read when**: Implementing token-based authentication, storing credentials in database, designing security-critical storage patterns, working with invitation or magic-link flows

### ADR-001: Separate Buyer Authentication Context
- **Status**: accepted
- **Date**: 2026-05-28
- **Bolt**: 008-customer-portal-service (002-customer-portal-service)
- **Path**: `bolts/008-customer-portal-service/adr-001-separate-buyer-auth-context.md`
- **Summary**: The platform serves two distinct user types (mayoristas and buyers) with different access patterns and security requirements. Use completely separate authentication contexts with different cookies, JWT structures, and database tables.
- **Read when**: Designing authentication systems, implementing authorization logic, working with buyer portal or mayorista endpoints, considering role-based access control, evaluating security boundaries between user types

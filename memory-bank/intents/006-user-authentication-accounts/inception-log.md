---
intent: 006-user-authentication-accounts
created: 2026-06-08T00:00:00Z
completed: 2026-06-08T00:00:00Z
status: complete
---

# Inception Log: user-authentication-accounts

## Overview

**Intent**: Foundational identity and access management — mayorista login (email+password + Google OAuth + mandatory 2FA), admin sub-role per tenant, and buyer token-based catalog access.
**Type**: green-field
**Created**: 2026-06-08

## Artifacts Created

| Artifact | Status | File |
|----------|--------|------|
| Requirements | ✅ | requirements.md |
| System Context | ✅ | system-context.md |
| Units | ✅ | units.md |
| Unit Brief — auth-service | ✅ | units/001-auth-service/unit-brief.md |
| Unit Brief — tenant-account-service | ✅ | units/002-tenant-account-service/unit-brief.md |
| Unit Brief — auth-accounts-ui | ✅ | units/003-auth-accounts-ui/unit-brief.md |
| Stories — auth-service | ✅ | units/001-auth-service/stories/ (9 stories) |
| Stories — tenant-account-service | ✅ | units/002-tenant-account-service/stories/ (7 stories) |
| Stories — auth-accounts-ui | ✅ | units/003-auth-accounts-ui/stories/ (8 stories) |
| Bolt Plan | ✅ | memory-bank/bolts/028–035 (8 bolts) |

## Summary

| Metric | Count |
|--------|-------|
| Functional Requirements | 9 |
| Non-Functional Requirements | 9 |
| Units | 3 |
| Stories | 24 |
| Bolts Planned | 8 |

## Units Breakdown

| Unit | Stories | Bolts | Priority |
|------|---------|-------|----------|
| 001-auth-service | 9 | 3 (030–032) | Must |
| 002-tenant-account-service | 7 | 2 (028–029) | Must |
| 003-auth-accounts-ui | 8 | 3 (033–035) | Must |

## Decision Log

| Date | Decision | Rationale | Approved |
|------|----------|-----------|----------|
| 2026-06-08 | Buyers use token links, not accounts | Mayoristas control buyer access; buyers should not manage credentials | Yes |
| 2026-06-08 | 2FA is mandatory and cannot be disabled by mayorista | Security requirement; subscription-gated disable left to future intent | Yes |
| 2026-06-08 | Subscription tiers out of scope | Separate intent to avoid scope creep | Yes |
| 2026-06-08 | JWT with RS256, short-lived access tokens (15min) | Stateless, scalable; asymmetric keys allow public verification | Yes |
| 2026-06-08 | Admin sub-role within mayorista tenant | Mayoristas need to delegate account management without sharing primary credentials | Yes |

## Scope Changes

| Date | Change | Reason | Impact |
|------|--------|--------|--------|

## Ready for Construction

**Checklist**:
- [x] All requirements documented
- [x] System context defined
- [x] Units decomposed
- [x] Stories created for all units
- [x] Bolts planned
- [x] Human review complete

## Next Steps

1. Begin Construction Phase
2. Start with Unit: `002-tenant-account-service` (foundational — introduces `tenant_id`)
3. Execute: `/specsmd-construction-agent --intent="006-user-authentication-accounts" --unit="002-tenant-account-service"`

## Dependencies

- Requires existing FastAPI backend and Next.js frontend (both present)
- Redis or DB token denylist (confirm infrastructure)
- Google OAuth app credentials (must be provisioned)
- Email delivery service (confirm provider)

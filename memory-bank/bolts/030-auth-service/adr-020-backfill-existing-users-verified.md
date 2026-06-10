---
adr: 020
bolt: 030-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
---

# ADR-020: Backfill Existing Users as Email Verified

## Context

The email verification feature is being introduced after the platform already has registered mayoristas. These existing users created accounts without an email verification step. The new schema includes `email_verified` (NOT NULL DEFAULT FALSE), which would lock out all existing users if not backfilled.

## Decision

During the Alembic migration, after adding the `email_verified` column:

1. Add column with `server_default=False` (safe default for new users)
2. Run a data migration statement: `UPDATE mayorista SET email_verified = true WHERE email_verified = false`
3. This marks all existing users as verified, allowing them to continue logging in

New users registering after this migration will have `email_verified = false` and must verify their email before logging in.

## Rationale

- **User experience**: Existing users are not locked out by a feature they never opted into
- **Security trade-off accepted**: Existing accounts bypass email verification — this is a known risk but acceptable since these users already proved identity through prior platform usage
- **Simplicity**: Single UPDATE statement in migration; no separate migration script needed
- **Forward-looking**: All new registrations go through verification

## Consequences

- **Positive**: Zero disruption to existing users; clean migration path
- **Negative**: Existing accounts have not verified email ownership; if an existing user's email was compromised, they could be locked out by a malicious registration attempt (mitigated by email uniqueness constraint)
- **Risk**: Low — existing users are known entities with platform history
- **Future**: If stricter verification is needed for existing users, a separate "re-verify" campaign can be launched

---
adr: 019
bolt: 030-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
---

# ADR-019: Extend Mayorista Model for Auth Features

## Context

The existing `Mayorista` model (`models/mayorista.py`) already represents the primary user type in the platform. It has `email`, `password_hash`, `tenant_id`, and `role` columns. The new auth features (email verification, account lockout, failed attempts tracking) require additional fields.

An alternative would be to create a new `User` model and migrate all `Mayorista` data to it, treating `Mayorista` as a role within a unified `User` entity.

## Decision

Extend the existing `Mayorista` model by adding the following columns:
- `email_verified` BOOLEAN NOT NULL DEFAULT FALSE
- `is_locked` BOOLEAN NOT NULL DEFAULT FALSE
- `failed_attempts` INTEGER NOT NULL DEFAULT 0
- `updated_at` TIMESTAMP WITH TIME ZONE

Do NOT create a new `User` model. The `Mayorista` table remains the primary user entity for this bolt's scope.

## Rationale

- **Minimal disruption**: All existing relationships (`prendas`, `media_items`, `vton_jobs`, `customers`, `tryoff_jobs`, `batch_jobs`) reference `Mayorista` — no FK changes needed
- **No data migration**: No need to copy or transform existing user records
- **Consistent with existing patterns**: The `Mayorista` model already has `tenant_id` and `role` from the multi-tenancy bolt (028)
- **Scope alignment**: This bolt covers mayorista auth only; buyer auth uses a separate `Customer` model (per ADR-001)
- **Future flexibility**: A unified `User` model can still be introduced later if buyer/mayorista convergence is needed

## Consequences

- **Positive**: Zero impact on existing relationships; simple Alembic migration (ADD COLUMN)
- **Negative**: The model name `Mayorista` is domain-specific rather than generic; may feel inconsistent if a `User` model is introduced later
- **Risk**: If a future `User` model is introduced, migration complexity increases (but this is deferred)
- **Note**: The `Mayorista` model's `Base` is defined in `models/mayorista.py` — new token models should import `Base` from the same module

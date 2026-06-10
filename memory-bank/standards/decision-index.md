---
last_updated: 2026-06-10T00:00:00Z
total_decisions: 21
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

### ADR-021: Atomic Failed Attempts Increment for Account Lockout
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 030-auth-service (001-auth-service)
- **Path**: `bolts/030-auth-service/adr-021-atomic-failed-attempts-increment.md`
- **Summary**: Use PostgreSQL atomic UPDATE with expression evaluation (`failed_attempts = failed_attempts + 1`) to increment the failed login counter. Row-level locking guarantees no lost updates under concurrent login attempts, with lockout triggered exactly at the 5th attempt in the same statement.
- **Read when**: Implementing account lockout, designing concurrent counter updates, preventing brute-force attacks, handling parallel authentication attempts

### ADR-020: Backfill Existing Users as Email Verified
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 030-auth-service (001-auth-service)
- **Path**: `bolts/030-auth-service/adr-020-backfill-existing-users-verified.md`
- **Summary**: During the Alembic migration, all existing mayoristas are marked as `email_verified = true` via a data migration UPDATE statement. New users registering after the migration must verify their email before logging in.
- **Read when**: Running migrations for new features affecting existing users, designing email verification flows, planning backward compatibility for auth features

### ADR-019: Extend Mayorista Model for Auth Features
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 030-auth-service (001-auth-service)
- **Path**: `bolts/030-auth-service/adr-019-extend-mayorista-model.md`
- **Summary**: The existing `Mayorista` model is extended with `email_verified`, `is_locked`, `failed_attempts`, and `updated_at` columns rather than creating a new `User` model. This avoids disrupting existing FK relationships and simplifies migration.
- **Read when**: Modifying the Mayorista model, designing authentication schema changes, adding new user attributes, planning model migrations

### ADR-018: Challenge Token Pattern for 2-Step Authentication
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 030-auth-service (001-auth-service)
- **Path**: `bolts/030-auth-service/adr-018-challenge-token-pattern.md`
- **Summary**: Login returns a short-lived (5-min) HS256-signed `challenge_token` encoding `user_id` and `step: credentials_passed` instead of a full JWT. The challenge_token must be presented to the 2FA endpoint along with the OTP code to receive a full JWT session.
- **Read when**: Implementing 2FA flows, designing multi-step authentication, working on login endpoints, building OAuth exchange flows

### ADR-017: Buyer Link Validation Returns 200 on Invalid Tokens
- **Status**: accepted
- **Date**: 2026-06-09
- **Bolt**: 029-tenant-account-service (002-tenant-account-service)
- **Path**: `bolts/029-tenant-account-service/adr-017-buyer-validation-200-response.md`
- **Summary**: The buyer link validation endpoint always returns HTTP 200, with invalid tokens returning { valid: false, reason: "..." } in the body. This avoids information leakage and simplifies frontend handling since buyers have no session to refresh.
- **Read when**: Designing public token validation endpoints, implementing stateless authorization flows, building unauthenticated API endpoints, reviewing error response patterns

### ADR-016: Redis Denylist for Admin Session Invalidation
- **Status**: accepted
- **Date**: 2026-06-09
- **Bolt**: 029-tenant-account-service (002-tenant-account-service)
- **Path**: `bolts/029-tenant-account-service/adr-016-redis-denylist-session-invalidation.md`
- **Summary**: Redis is introduced as a new infrastructure dependency for session invalidation on admin revocation. Revoked admin refresh token JTIs are stored in Redis with TTL matching the original token's remaining lifetime. The 15-minute access token window remains an accepted risk.
- **Read when**: Implementing session management, adding new infrastructure dependencies, designing token revocation flows, configuring Docker Compose or k3s deployments, evaluating Redis vs PostgreSQL for ephemeral data

### ADR-015: Postgres RLS Deferred as Future Defense-in-Depth
- **Status**: accepted
- **Date**: 2026-06-09
- **Bolt**: 028-tenant-account-service (002-tenant-account-service)
- **Path**: `bolts/028-tenant-account-service/adr-015-rls-deferred.md`
- **Summary**: Postgres Row Level Security is deferred for the initial multi-tenancy release. Application-level tenant isolation (FastAPI dependency + SQLAlchemy event listener) provides sufficient protection. RLS should be evaluated after the initial release is stable.
- **Read when**: Designing database-level access control, implementing tenant isolation hardening, evaluating PostgreSQL security features, planning security audits

### ADR-014: Stateless Buyer Link Validation with Audit Trail
- **Status**: accepted
- **Date**: 2026-06-09
- **Bolt**: 028-tenant-account-service (002-tenant-account-service)
- **Path**: `bolts/028-tenant-account-service/adr-014-stateless-buyer-link-validation.md`
- **Summary**: Buyer link validation is stateless JWT verification (no DB lookup) to meet the < 150ms latency requirement. The buyer_links table serves as an audit trail only. Links cannot be revoked before expiration.
- **Read when**: Implementing buyer catalog access, designing token validation flows, optimizing authentication latency, building stateless authorization systems

### ADR-013: Multi-Step Alembic Migration with Default Tenant Backfill
- **Status**: accepted
- **Date**: 2026-06-09
- **Bolt**: 028-tenant-account-service (002-tenant-account-service)
- **Path**: `bolts/028-tenant-account-service/adr-013-alembic-migration-strategy.md`
- **Summary**: A 7-step atomic Alembic migration introduces tenant_id to all platform tables. A default tenant is created first, then existing rows are backfilled, then NOT NULL and FK constraints are added. Runs in a single transaction with rollback on failure.
- **Read when**: Running multi-tenancy migrations, adding NOT NULL columns to tables with existing data, designing database backfill strategies, planning zero-downtime schema changes

### ADR-012: Multi-Layer Tenant Isolation Enforcement
- **Status**: accepted
- **Date**: 2026-06-09
- **Bolt**: 028-tenant-account-service (002-tenant-account-service)
- **Path**: `bolts/028-tenant-account-service/adr-012-tenant-isolation-strategy.md`
- **Summary**: Tenant isolation is enforced at two layers: FastAPI dependency injection (primary) and SQLAlchemy before_compile event listener (secondary). Both layers must agree, providing defense-in-depth against cross-tenant data leaks.
- **Read when**: Implementing multi-tenant query scoping, designing tenant isolation middleware, adding new endpoints that access tenant-scoped data, reviewing security boundaries between tenants

### ADR-011: Celery Retry with Error Flag for Media Save Failures
- **Status**: accepted
- **Date**: 2026-06-04
- **Bolt**: 025-batch-job-service (001-batch-job-service)
- **Path**: `bolts/025-batch-job-service/adr-011-media-save-retry-strategy.md`
- **Summary**: Retry media save up to 3 times with exponential backoff on MinIO failures. If all retries fail, set `media_save_error` flag on the batch item for manual re-save by the mayorista.
- **Read when**: Implementing media library save operations, designing Celery retry policies for external service calls, handling transient storage failures, building graceful degradation patterns

### ADR-010: Unique Constraint on vton_job_id in Media Items for Idempotency
- **Status**: accepted
- **Date**: 2026-06-04
- **Bolt**: 025-batch-job-service (001-batch-job-service)
- **Path**: `bolts/025-batch-job-service/adr-010-media-save-idempotency.md`
- **Summary**: Add unique constraint on `media_items.vton_job_id` to prevent duplicate media entries from duplicate Celery callbacks. Application-level fast-path check (`result_media_id IS NOT NULL`) avoids unnecessary DB inserts for already-saved items.
- **Read when**: Implementing idempotent media save operations, designing Celery callback idempotency, preventing duplicate records from duplicate task execution, adding unique constraints to existing tables

### ADR-009: Atomic Counter Updates via SQLAlchemy F() Expressions
- **Status**: accepted
- **Date**: 2026-06-04
- **Bolt**: 024-batch-job-service (001-batch-job-service)
- **Path**: `bolts/024-batch-job-service/adr-009-atomic-counter-updates.md`
- **Summary**: Use `UPDATE ... SET count = count + 1` with `RETURNING` for batch counter updates. PostgreSQL row-level locking guarantees no lost updates under concurrent Celery workers, with a single round-trip query.
- **Read when**: Implementing concurrent counter increments, designing Celery completion callbacks, handling parallel updates to shared aggregates, preventing lost update race conditions

### ADR-008: Explicit Callback in VtonJob Task for Batch Completion
- **Status**: accepted
- **Date**: 2026-06-04
- **Bolt**: 024-batch-job-service (001-batch-job-service)
- **Path**: `bolts/024-batch-job-service/adr-008-explicit-callback-vs-signals.md`
- **Summary**: Add an explicit conditional callback call at the end of the existing `process_vton_job` task to handle batch item status updates. Only fires when `VtonJob.batch_item_id` is set, keeping single-item VTON flows unaffected.
- **Read when**: Extending Celery tasks with new side-effects, designing completion callbacks for async jobs, adding batch-aware behavior to existing task flows, choosing between signal handlers and explicit callbacks

### ADR-007: Sequential Celery Task Publishing for Batch Enqueue
- **Status**: accepted
- **Date**: 2026-06-04
- **Bolt**: 023-batch-job-service (001-batch-job-service)
- **Path**: `bolts/023-batch-job-service/adr-007-sequential-celery-enqueue.md`
- **Summary**: Use FastAPI BackgroundTasks to publish Celery tasks after the HTTP response is sent, keeping the API within the 500ms budget. DB commit is the critical path; Celery publishing is fire-and-forget with reconciliation for failure cases.
- **Read when**: Implementing batch job submission, designing async task publishing patterns, optimizing API response times for bulk operations, configuring background task execution

### ADR-006: Backwards-Compatible batch_item_id FK on VtonJob
- **Status**: accepted
- **Date**: 2026-06-04
- **Bolt**: 023-batch-job-service (001-batch-job-service)
- **Path**: `bolts/023-batch-job-service/adr-006-vtonjob-batch-item-fk.md`
- **Summary**: Add a nullable `batch_item_id` FK to the existing `vton_jobs` table to link VTON jobs to their parent batch item. Existing single-item VTON flows are unaffected; completion callback checks for NULL before updating batch counters.
- **Read when**: Modifying the VtonJob model, designing cross-domain schema references, implementing completion callbacks, adding optional foreign keys to existing tables

### ADR-005: Use SQLAlchemy transaction.on_commit for Celery Task Publishing
- **Status**: accepted
- **Date**: 2026-06-04
- **Bolt**: 023-batch-job-service (001-batch-job-service)
- **Path**: `bolts/023-batch-job-service/adr-005-transactional-celery-publish.md`
- **Summary**: Defer Celery task publishing until after the database transaction commits to prevent orphaned tasks. If DB commit fails, no tasks are sent. If Celery publish fails after commit, batch exists but items are not enqueued (requires retry).
- **Read when**: Implementing async job orchestration, coordinating database writes with message broker publishing, designing distributed transaction patterns, preventing orphaned background tasks

### ADR-004: Separate Celery Queue for TryOff Jobs
- **Status**: accepted
- **Date**: 2026-05-31
- **Bolt**: 016-tryoff-job-service (002-tryoff-job-service)
- **Path**: `bolts/016-tryoff-job-service/adr-001-separate-celery-queue.md`
- **Summary**: Use a dedicated Celery queue named `tryoff` for all TryOff job processing, separate from the existing `vton` queue, to prevent job starvation and ensure predictable processing times.
- **Read when**: Implementing async job processing, designing Celery task routing, adding new AI-powered features that require background processing, configuring worker pools, troubleshooting job queue performance

### ADR-003: Build-Time Weight Download for FLUX.2-klein Model
- **Status**: accepted
- **Date**: 2026-05-31
- **Bolt**: 014-tryoff-model-service (001-tryoff-model-service)
- **Path**: `bolts/014-tryoff-model-service/adr-003-build-time-weight-download.md`
- **Summary**: The TryOff model service requires FLUX.2-klein-base-9B (~18 GB) and virtual-tryoff-lora weights. Download weights at Docker image build time rather than runtime to ensure deterministic startup and avoid 30+ minute first-start latency.
- **Read when**: Setting up new AI model containers, designing Docker images for GPU services, evaluating weight management strategies, planning CI/CD for ML inference services

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

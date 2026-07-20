---
last_updated: 2026-07-18T06:47:24Z
total_decisions: 45
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

### ADR-045: Pass Tenant Context Through Internal Batch Submission
- **Status**: accepted
- **Date**: 2026-07-18
- **Bolt**: 030-pose-set-service (002-pose-set-service)
- **Path**: `bolts/030-pose-set-service/adr-045-tenant-aware-batch-contract.md`
- **Summary**: Pass authenticated `tenant_id` explicitly through public and internal batch submission so non-null BatchJob tenancy is preserved without duplicating batch logic.
- **Read when**: Calling batch creation from another service, modifying BatchJob submission signatures, or implementing tenant-scoped workflows

### ADR-044: Store ModelPhoto IDs in Pose-Set Batch Items
- **Status**: accepted
- **Date**: 2026-07-18
- **Bolt**: 030-pose-set-service (002-pose-set-service)
- **Path**: `bolts/030-pose-set-service/adr-044-batch-item-model-photo-reference.md`
- **Summary**: PoseSet submissions store selected `ModelPhoto.id` values in the existing `BatchItem.model_id` field, preserving the VTON input contract and enabling direct pose mapping without schema duplication.
- **Read when**: Mapping pose-set selections into BatchItems, resolving result items to ModelPhoto.pose, or considering BatchItem schema changes

### ADR-043: PoseSet and Batch Creation Share One Transaction
- **Status**: accepted
- **Date**: 2026-07-18
- **Bolt**: 030-pose-set-service (002-pose-set-service)
- **Path**: `bolts/030-pose-set-service/adr-043-poseset-batch-atomicity.md`
- **Summary**: PoseSet validation, delegated BatchJob/BatchItem creation, and PoseSet insertion share one AsyncSession transaction and commit, preventing orphaned grouping or batch records.
- **Read when**: Coordinating PoseSet and BatchJob writes, changing internal batch service transaction boundaries, or testing partial submission failures

### ADR-042: Batched Autocommit Pattern for Alembic Data Migrations
- **Status**: accepted
- **Date**: 2026-07-18
- **Bolt**: 029-model-pose-service (001-model-pose-service)
- **Path**: `bolts/029-model-pose-service/adr-042-batched-autocommit-data-migrations.md`
- **Summary**: Large Alembic data migrations use `autocommit_block()` with per-batch commits, an idempotent selection predicate, and guarded atomic updates to limit locks and support safe resumption.
- **Read when**: Writing Alembic data migrations over large tables, deploying migrations against a live API, or designing resume-after-failure behavior

### ADR-041: No-Op Downgrade for Backfill-Type Data Migrations
- **Status**: accepted
- **Date**: 2026-07-18
- **Bolt**: 029-model-pose-service (001-model-pose-service)
- **Path**: `bolts/029-model-pose-service/adr-041-noop-downgrade-data-migrations.md`
- **Summary**: Backfills that create identity rows are intentionally irreversible because generated wrappers are indistinguishable from user-created rows; schema rollback remains with the owning schema migration.
- **Read when**: Writing downgrade functions for data migrations, planning rollback strategy, or reviewing migration data-loss risk

### ADR-040: Return 404 (Not 403) for Unowned Resource Access
- **Status**: accepted
- **Date**: 2026-07-18
- **Bolt**: 028-model-pose-service (001-model-pose-service)
- **Path**: `bolts/028-model-pose-service/adr-013-404-for-unowned-resources.md`
- **Summary**: Ownership-scoped endpoints return `404 Not Found` when a resource does not exist or belongs to another mayorista, preventing resource-existence leaks.
- **Read when**: Designing ownership-scoped API endpoints or choosing between 403 and 404 responses

### ADR-039: Extend `model_photos` Table for Pose Photos
- **Status**: accepted
- **Date**: 2026-07-18
- **Bolt**: 028-model-pose-service (001-model-pose-service)
- **Path**: `bolts/028-model-pose-service/adr-012-extend-model-photos-table.md`
- **Summary**: Extend the existing `model_photos` table with nullable `model_id` and `pose` columns instead of creating a parallel pose-photo table.
- **Read when**: Modifying the ModelPhoto model or querying curated versus pose photos

### ADR-038: AWS IAM Credentials for EKS Access from GitHub Actions
- **Status**: accepted
- **Date**: 2026-06-18
- **Bolt**: 040-ci-cd-pipeline (006-ci-cd-pipeline)
- **Path**: `bolts/040-ci-cd-pipeline/adr-038-aws-iam-eks-access.md`
- **Summary**: GitHub Actions uses AWS IAM credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) stored as GitHub environment secrets to authenticate to EKS via `aws eks update-kubeconfig`. This replaces the previous base64-encoded kubeconfig approach used for bare-metal k3s. EKS natively integrates with AWS IAM, eliminating the need for static kubeconfig tokens.
- **Read when**: Configuring GitHub Actions access to the EKS cluster, rotating AWS credentials in CI, evaluating IAM-based Kubernetes authentication

### ADR-037: Migration Job backoffLimit: 0 — Fail Fast, No Auto-Retry
- **Status**: accepted
- **Date**: 2026-06-18
- **Bolt**: 041-database-migrations (005-db-migrations)
- **Path**: `bolts/041-database-migrations/adr-037-migration-job-backoff-zero.md`
- **Summary**: The Alembic migration Job sets `backoffLimit: 0`. On pod failure, Kubernetes stops immediately — no auto-retry. Operator must inspect DB state before retrying. Auto-retry risks applying DDL a second time (already exists) or retrying after partial schema changes, producing confusing secondary errors.
- **Read when**: Configuring a k8s Job that modifies shared persistent state, debugging a failed migration Job, deciding retry policy for batch Jobs, evaluating whether to use backoffLimit > 0 for DB jobs

### ADR-036: Redis as Deployment (No PVC) for Staging
- **Status**: accepted
- **Date**: 2026-06-18
- **Bolt**: 039-kubernetes-config (004-kubernetes-deployment-config)
- **Path**: `bolts/039-kubernetes-config/adr-036-redis-deployment-no-pvc.md`
- **Summary**: Redis runs as a Deployment with no PersistentVolumeClaim for staging. The token denylist (used for logout revocation) is in-memory only; pod restart causes up to 7-day token revocation gap. Accepted for staging; production should re-evaluate StatefulSet + PVC or managed Redis.
- **Read when**: Implementing logout/force-logout flows, reviewing token revocation security, planning Redis migration to StatefulSet, auditing session management, designing production Redis deployment

### ADR-035: ingress-nginx with NLB on EKS (Over hostNetwork on k3s)
- **Status**: accepted
- **Date**: 2026-06-18
- **Bolt**: 039-kubernetes-config (004-kubernetes-deployment-config)
- **Path**: `bolts/039-kubernetes-config/adr-035-ingress-nginx-nlb.md`
- **Summary**: ingress-nginx is deployed as a Deployment with a LoadBalancer Service annotated to create an AWS NLB. This replaces the previous hostNetwork approach used on k3s. Nodes are in private subnets; NLB provides the public entry point. ~$16/month for NLB.
- **Read when**: Configuring ingress controller on EKS, troubleshooting Ingress routing, setting up TLS with cert-manager, planning horizontal scaling

### ADR-034: S3 Backend for Terraform State (Over Terraform Cloud + Hetzner)
- **Status**: accepted
- **Date**: 2026-06-18
- **Bolt**: 037-infrastructure (002-infrastructure-provisioning)
- **Path**: `bolts/037-infrastructure/adr-034-s3-state-backend.md`
- **Summary**: AWS S3 with DynamoDB locking is the Terraform state backend. Replaces Terraform Cloud (primary) + Hetzner Object Storage (fallback). Native AWS integration, state locking via DynamoDB, S3 versioning for history, KMS encryption.
- **Read when**: Adding new Terraform workspaces, migrating state backends, setting up CI/CD pipelines that run terraform, debugging state lock issues

### ADR-033: EBS CSI Driver for Persistent Storage (Over local-path-provisioner)
- **Status**: accepted
- **Date**: 2026-06-18
- **Bolt**: 037-infrastructure (002-infrastructure-provisioning)
- **Path**: `bolts/037-infrastructure/adr-033-ebs-csi-storage.md`
- **Summary**: AWS EBS gp3 volumes via EBS CSI Driver for all StatefulSet PVs. Replaces k3s local-path-provisioner. Volumes are network-attached and survive node replacement. EBS snapshots available for backup. ~$0.08/GB/month for gp3.
- **Read when**: Adding a new StatefulSet to the cluster, planning disaster recovery, evaluating storage options, debugging PV binding issues

### ADR-032: Managed EKS Over Self-Managed k3s on Hetzner
- **Status**: accepted
- **Date**: 2026-06-18
- **Bolt**: 037-infrastructure (002-infrastructure-provisioning)
- **Path**: `bolts/037-infrastructure/adr-032-managed-eks.md`
- **Summary**: AWS EKS with managed node groups (2x t3.large) replaces self-managed k3s on Hetzner. AWS manages control plane (API server, etcd, scheduler). ~$73/month for EKS control plane. Region: us-west-2 (Oregon).
- **Read when**: Planning cluster upgrades, debugging control-plane availability, adding worker nodes, evaluating Kubernetes version compatibility

### ADR-031: Frontend node_modules Named Volume Overlay in Docker Compose
- **Status**: accepted
- **Date**: 2026-06-17
- **Bolt**: 036-dev-environment (001-dev-environment)
- **Path**: `bolts/036-dev-environment/adr-031-node-modules-named-volume-overlay.md`
- **Summary**: Mount a Docker named volume at `/app/node_modules` alongside the source bind mount at `/app` to ensure container-compiled packages (correct Linux architecture) shadow any host-side node_modules. Prevents silent architecture-mismatch failures on macOS/Windows.
- **Read when**: Adding a new frontend service to docker-compose, troubleshooting missing npm packages inside a container, configuring hot-reload for any Node.js service, or debugging native binary errors (sharp, esbuild) in a containerized frontend

### ADR-030: Alembic Migrations Run in Backend Entrypoint (Dev) / Kubernetes Job (Prod)
- **Status**: accepted
- **Date**: 2026-06-17
- **Bolt**: 036-dev-environment (001-dev-environment)
- **Path**: `bolts/036-dev-environment/adr-030-alembic-entrypoint-migration.md`
- **Summary**: In docker-compose dev, `alembic upgrade head` runs inside the backend container entrypoint before uvicorn starts (idempotent, fails loudly). In production k8s (bolts 039/041), migrations run as a dedicated Kubernetes Job — the entrypoint pattern is explicitly rejected for production due to multi-replica race conditions.
- **Read when**: Configuring backend container startup, designing k8s deployment for the backend, adding new Alembic migrations, debugging backend startup failures, or configuring celery_worker (must NOT include migration step)

### ADR-029: Password Reset Revokes All Active Sessions
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 032-auth-service (001-auth-service)
- **Path**: `bolts/032-auth-service/adr-029-password-reset-revokes-sessions.md`
- **Summary**: On password reset, all refresh tokens are revoked in DB and JTIs added to Redis denylist. Existing access tokens remain valid for up to 15 minutes (accepted risk, NIST SP 800-63B compliant). No access token denylist introduced.
- **Read when**: Implementing password reset flows, designing session invalidation on credential change, reviewing security policies for account recovery

### ADR-028: Immediate Denylist on Token Rotation
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 032-auth-service (001-auth-service)
- **Path**: `bolts/032-auth-service/adr-028-immediate-denylist-on-rotation.md`
- **Summary**: Old refresh token JTI added to Redis denylist via SETNX before new token is issued. Prevents concurrent refresh race conditions. First refresh succeeds, concurrent duplicates fail with 401.
- **Read when**: Implementing token refresh endpoints, designing refresh token rotation, handling concurrent authentication requests, preventing token replay attacks

### ADR-027: Fail-Closed on Redis Outage for Token Refresh
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 032-auth-service (001-auth-service)
- **Path**: `bolts/032-auth-service/adr-027-fail-closed-redis-outage.md`
- **Summary**: When Redis denylist is unavailable during refresh, returns 503 instead of allowing potentially revoked tokens. Existing 15-minute access tokens provide grace period.
- **Read when**: Designing authentication failure modes, planning Redis outage procedures, configuring monitoring and alerting for auth services, evaluating security vs availability trade-offs

### ADR-026: RS256 Asymmetric Signing for Access Tokens
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 032-auth-service (001-auth-service)
- **Path**: `bolts/032-auth-service/adr-026-rs256-asymmetric-signing.md`
- **Summary**: Access tokens signed with RS256 (RSA 2048-bit). Private key from JWT_PRIVATE_KEY env var. Public key served at /.well-known/jwks.json. Enables downstream service verification without sharing secrets.
- **Read when**: Implementing JWT verification in downstream services, configuring public key endpoints, designing key rotation strategies, integrating third-party services with auth

### ADR-025: Challenge Token Single-Use via Redis Tracking
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 031-auth-service (001-auth-service)
- **Path**: `bolts/031-auth-service/adr-025-challenge-token-single-use.md`
- **Summary**: Challenge tokens are tracked in Redis via `challenge:consumed:{jti}` with 300s TTL using atomic SETNX to enforce single-use consumption. Prevents replay of challenge tokens to obtain multiple JWT sessions.
- **Read when**: Implementing 2FA challenge flows, OAuth exchange endpoints, designing single-use token patterns, working with challenge token lifecycle

### ADR-024: OAuth Account Linking Requires Password Confirmation
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 031-auth-service (001-auth-service)
- **Path**: `bolts/031-auth-service/adr-024-oauth-account-linking-security.md`
- **Summary**: When Google OAuth email matches an existing email+password account, the user must enter their password to confirm the link. Prevents account takeover via compromised OAuth provider.
- **Read when**: Implementing OAuth identity linking, designing account merge flows, working on Google login, reviewing authentication security boundaries

### ADR-023: Redis as Primary Store for Ephemeral Auth State
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 031-auth-service (001-auth-service)
- **Path**: `bolts/031-auth-service/adr-023-redis-ephemeral-auth-state.md`
- **Summary**: Redis stores all ephemeral auth state (TOTP replay protection, SMS rate limiting, OTP hashes, challenge token consumption) with automatic TTL expiration. Graceful degradation if Redis is unavailable.
- **Read when**: Designing ephemeral auth storage, implementing rate limiting or replay protection, configuring Redis for authentication, planning graceful degradation strategies

### ADR-022: Fernet Symmetric Encryption for Sensitive Auth Fields
- **Status**: accepted
- **Date**: 2026-06-10
- **Bolt**: 031-auth-service (001-auth-service)
- **Path**: `bolts/031-auth-service/adr-022-fernet-symmetric-encryption.md`
- **Summary**: TOTP secrets and phone numbers are encrypted with Fernet (AES-128-CBC + HMAC-SHA256) using a key from `TWO_FACTOR_ENCRYPTION_KEY` env var. Establishes the project's symmetric encryption pattern.
- **Read when**: Storing sensitive reversible data, designing encryption for secrets or PII, implementing symmetric encryption patterns, managing encryption keys

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

# Global Story Index

## Overview
- **Total stories**: 167
- **Generated**: 167
- **Last updated**: 2026-07-01

---

## Stories by Intent

### 001-vton-generation-pipeline

#### Unit: 001-media-service

- [x] **001-upload-garment-photo** ✅ GENERATED — Upload Garment Photo — Must
- [x] **002-upload-own-model-photo** ✅ GENERATED — Upload Own Model Photo — Must
- [x] **003-curated-model-library** ✅ GENERATED — Browse Curated Model Library — Must

#### Unit: 002-vton-job-service

- [x] **001-submit-vton-job** ✅ GENERATED — Submit VTON Job — Must
- [x] **002-process-job-celery** ✅ GENERATED — Process Job via Celery Worker — Must
- [x] **003-poll-job-status** ✅ GENERATED — Poll Job Status — Must
- [x] **004-retry-on-failure** ✅ GENERATED — Automatic Retry on Failure — Must
- [x] **005-job-history** ✅ GENERATED — Job History — Should

#### Unit: 003-vton-pipeline-ui

- [x] **001-garment-upload-ui** ✅ GENERATED — Garment Upload Form — Must
- [x] **002-model-selection-ui** ✅ GENERATED — Model Selection UI — Must
- [x] **003-job-submission-ui** ✅ GENERATED — Job Submission Form — Must
- [x] **004-job-status-polling-ui** ✅ GENERATED — Job Status Polling UI — Must
- [x] **005-result-display-ui** ✅ GENERATED — Result Display — Must
- [x] **006-job-history-ui** ✅ GENERATED — Job History Page — Should

---

### 002-catalog-management

#### Unit: 001-catalog-service

- [x] **001-create-catalog** ✅ GENERATED — Create Named Catalog — Must
- [x] **002-add-catalog-item** ✅ GENERATED — Add Item to Catalog — Must
- [x] **003-remove-catalog-item** ✅ GENERATED — Remove Item from Catalog — Must
- [x] **004-reorder-catalog-items** ✅ GENERATED — Reorder Catalog Items — Must
- [x] **005-rename-catalog** ✅ GENERATED — Rename Catalog — Must
- [x] **006-publish-unpublish-catalog** ✅ GENERATED — Publish / Unpublish Catalog — Must
- [x] **007-delete-catalog** ✅ GENERATED — Delete Catalog — Must
- [x] **008-list-catalogs** ✅ GENERATED — List Mayorista's Catalogs — Must

#### Unit: 002-customer-portal-service

- [x] **001-register-customer** ✅ GENERATED — Register Buyer / Customer — Must
- [x] **002-buyer-portal-auth** ✅ GENERATED — Buyer Portal Authentication — Must
- [x] **003-browse-published-catalogs** ✅ GENERATED — Browse Published Catalogs — Must

#### Unit: 003-catalog-management-ui

- [x] **001-catalog-list-page** ✅ GENERATED — Catalog Dashboard (Mayorista) — Must
- [x] **002-catalog-detail-page** ✅ GENERATED — Catalog Detail & Item Management — Must
- [x] **003-catalog-publish-flow** ✅ GENERATED — Publish / Unpublish Catalog Flow — Must
- [x] **004-customer-management-page** ✅ GENERATED — Customer Management Page — Must
- [x] **005-buyer-portal-page** ✅ GENERATED — Buyer Portal Catalog Browser — Must

---

---

### 003-fashn-provider-upgrade

#### Unit: 001-fashn-postprocess

- [x] **001-hand-compositing-tuning** ✅ GENERATED — Tune Hand Compositing to Eliminate Artifacts — Must
- [x] **002-long-pants-threshold-validation** ✅ GENERATED — Validate and Tune Long-Pants Detection Thresholds — Must
- [x] **003-segmentation-free-ab-test** ✅ GENERATED — A/B Test segmentation_free for One-Pieces — Should
- [x] **004-full-resolution-model-image** ✅ GENERATED — Compare Thumbnail vs Full-Res Model Input — Could

#### Unit: 002-fashn-validation

- [x] **001-container-deployment-reliability** ✅ GENERATED — Fix Stale Container; Add Version Logging — Must
- [x] **002-multi-subject-test-suite** ✅ GENERATED — Source ≥3 Subjects; Run and Document Test Suite — Must

---

---

### 004-tryoff-garment-extraction

#### Unit: 001-tryoff-model-service

- [x] **001-flux-container-setup** ✅ GENERATED — FLUX.2-klein Container with LoRA Weights — Must
- [x] **002-tryoff-inference-api** ✅ GENERATED — POST /tryoff Inference Endpoint — Must
- [x] **003-container-health-monitoring** ✅ GENERATED — Health Check + Auto-Restart — Must

#### Unit: 002-tryoff-job-service

- [x] **001-submit-tryoff-job** ✅ GENERATED — Submit TryOff Extraction Job — Must
- [x] **002-process-job-celery** ✅ GENERATED — Process Extraction Job via Celery — Must
- [x] **003-multi-garment-queue** ✅ GENERATED — Queue Multiple Garments from One Image — Must
- [x] **004-poll-job-status** ✅ GENERATED — Poll Job Status and Retrieve Output — Must
- [x] **005-media-library-save** ✅ GENERATED — Auto-Save Extracted Garment to Media Library — Must
- [x] **006-retry-on-failure** ✅ GENERATED — Auto-Retry Failed Jobs — Should
- [x] **007-job-history** ✅ GENERATED — TryOff Job History — Should

#### Unit: 003-tryoff-pipeline-ui

- [x] **001-source-image-upload-page** ✅ GENERATED — Source Image Upload Page — Must
- [x] **002-garment-type-selector** ✅ GENERATED — Garment Type Multi-Selector — Must
- [x] **003-extraction-status-display** ✅ GENERATED — Extraction Job Status Display — Must
- [x] **004-extracted-garment-gallery** ✅ GENERATED — Extracted Garments in Media Library — Must
- [x] **005-vton-handoff-action** ✅ GENERATED — One-Click VTON Handoff — Should
- [x] **006-extraction-result-preview** ✅ PLANNED — Extracted Garment Full-Size Preview on Flat Background — Should

---

---

### 005-batch-vton-generation

#### Unit: 001-batch-job-service

- [x] **001-create-batch-job** ✅ GENERATED — Create BatchJob and Persist Items — Must
- [x] **002-enqueue-batch-items** ✅ GENERATED — Enqueue All Items as VtonJobs — Must
- [x] **003-track-item-status** ✅ GENERATED — Track Per-Item Status via Celery Callback — Must
- [x] **004-partial-failure-isolation** ✅ GENERATED — Partial Failure Isolation — Must
- [x] **005-retry-failed-item** ✅ GENERATED — Retry Failed Batch Item — Must
- [x] **006-auto-save-to-media-library** ✅ GENERATED — Auto-Save Completed Item to Media Library — Must
- [x] **007-batch-history** ✅ GENERATED — Batch History API — Should

#### Unit: 002-batch-vton-generation-ui

- [x] **001-batch-creation-flow** ✅ GENERATED — Batch Creation Flow — Must
- [x] **002-batch-progress-page** ✅ GENERATED — Batch Progress Page — Must
- [x] **003-retry-failed-item-ui** ✅ GENERATED — Retry Failed Item UI — Must
- [x] **004-batch-history-page** ✅ GENERATED — Batch History Page — Should

---

---

### 006-user-authentication-accounts

#### Unit: 001-auth-service

- [x] **001-mayorista-registration** ✅ GENERATED — Mayorista Registration — Must
- [x] **002-email-verification** ✅ GENERATED — Email Verification — Must
- [x] **003-login-email-password** ✅ GENERATED — Login with Email + Password — Must
- [x] **004-account-lockout** ✅ GENERATED — Account Lockout on Failed Attempts — Must
- [x] **005-totp-2fa-setup-and-challenge** ✅ GENERATED — TOTP 2FA Setup and Challenge — Must
- [x] **006-sms-otp-2fa-fallback** ✅ GENERATED — SMS OTP 2FA Fallback — Must
- [x] **007-google-oauth-login** ✅ GENERATED — Google OAuth Login via NextAuth — Must
- [x] **008-password-reset** ✅ GENERATED — Password Reset Flow — Must
- [x] **009-jwt-session-management** ✅ GENERATED — JWT Session Management and Logout — Must

#### Unit: 002-tenant-account-service

- [x] **001-create-manage-tenant** ✅ GENERATED — Create and Manage Tenant — Must
- [x] **002-tenant-isolation-middleware** ✅ GENERATED — Tenant Isolation Middleware + Migration — Must
- [x] **003-cross-tenant-access-returns-404** ✅ GENERATED — Cross-Tenant Access Returns 404 — Must
- [x] **004-generate-buyer-catalog-link** ✅ GENERATED — Generate Buyer Catalog Access Link — Must
- [x] **005-validate-buyer-catalog-link** ✅ GENERATED — Validate Buyer Catalog Access Link — Must
- [x] **006-invite-admin-to-tenant** ✅ GENERATED — Invite Admin to Tenant — Should
- [x] **007-revoke-admin-access** ✅ GENERATED — Revoke Admin Access — Should

#### Unit: 003-auth-accounts-ui

- [x] **001-registration-email-verification-pages** ✅ GENERATED — Registration & Email Verification Pages — Must
- [x] **002-login-page-google-oauth** ✅ GENERATED — Login Page with Google OAuth — Must
- [x] **003-2fa-setup-wizard** ✅ GENERATED — 2FA Setup Wizard — Must
- [x] **004-2fa-challenge-screen** ✅ GENERATED — 2FA Challenge Screen — Must
- [x] **005-password-reset-pages** ✅ GENERATED — Password Reset Pages — Must
- [x] **006-buyer-catalog-access-page** ✅ GENERATED — Buyer Catalog Access Page — Must
- [x] **007-session-aware-routing-auth-guard** ✅ GENERATED — Session-Aware Routing and Auth Guard — Must
- [x] **008-account-settings-admin-buyer-links** ✅ GENERATED — Account Settings — Admin Management & Buyer Links — Should

---

---

### 007-multi-environment-deployment

#### Unit: 001-dev-environment

- [x] **001-refactor-docker-compose** ✅ COMPLETE — Refactor docker-compose.yml — Must
- [x] **002-configure-alembic-auto** ✅ COMPLETE — Configure Alembic auto-migration on startup — Must
- [x] **003-hot-reload-frontend** ✅ COMPLETE — Enable hot-reload for frontend development — Must
- [x] **004-hot-reload-backend** ✅ COMPLETE — Enable hot-reload for backend development — Must
- [x] **005-env-example** ✅ COMPLETE — Create and document .env.example template — Must
- [x] **006-test-dev-startup** ✅ COMPLETE — Test full development environment startup — Must
- [x] **007-dev-guide** ✅ COMPLETE — Document local development quick-start guide — Should

#### Unit: 002-infrastructure-provisioning

- [x] **001-terraform-structure** ✅ COMPLETE — Design Terraform project structure for hcloud — Must
- [x] **002-terraform-variables** ✅ COMPLETE — Create Terraform variables and outputs — Must
- [x] **003-hcloud-vpc** ✅ COMPLETE — Provision Hetzner VPC and networking — Must
- [x] **004-k3s-control-plane** ✅ COMPLETE — Provision CX21 control plane node with k3s — Must
- [x] **005-k3s-worker** ✅ COMPLETE — Provision CX31 worker node with k3s — Must
- [x] **006-node-configuration** ✅ COMPLETE — Configure node labels and taints — Must
- [x] **007-persistent-volumes** ✅ COMPLETE — Implement persistent volume provisioning — Must
- [x] **008-backup-cronjob** ✅ COMPLETE — Create PostgreSQL backup cronjob — Must
- [x] **009-test-backup** ✅ COMPLETE — Test backup creation and storage — Must
- [x] **010-test-restore** ✅ COMPLETE — Test restore procedure from backup — Must
- [x] **011-ops-documentation** ✅ COMPLETE — Document cluster management procedures — Should
- [x] **012-terraform-state** ✅ COMPLETE — Implement Terraform remote state backend — Should

#### Unit: 003-container-optimization

- [x] **001-analyze-dockerfile** ✅ COMPLETE — Analyze current Dockerfile or create new — Must
- [x] **002-frontend-docker** ✅ COMPLETE — Design frontend Dockerfile with multi-stage build — Must
- [x] **003-backend-docker** ✅ COMPLETE — Design backend Dockerfile with multi-stage build — Must
- [x] **004-frontend-health** ✅ COMPLETE — Implement /health endpoint in frontend — Must
- [x] **005-backend-health** ✅ COMPLETE — Implement /health endpoint in backend — Must
- [x] **006-health-check-instruction** ✅ COMPLETE — Add HEALTHCHECK instruction to Dockerfiles — Must
- [x] **007-nonroot-user** ✅ COMPLETE — Create non-root user configuration — Must
- [x] **008-optimize-layers** ✅ COMPLETE — Optimize image layers and dependencies — Must
- [x] **009-build-documentation** ✅ COMPLETE — Document build process and optimization techniques — Must
- [x] **010-test-images** ✅ COMPLETE — Test image builds and validate sizes — Must
- [x] **011-security-scan** ✅ COMPLETE — Run security scan on images (Trivy) — Must
- [x] **012-push-to-registry** ✅ COMPLETE — Push images to registry and validate pull — Should

#### Unit: 004-kubernetes-config

- [x] **001-manifest-structure** ✅ COMPLETE — Design k8s manifest folder structure — Must
- [x] **002-frontend-deployment** ✅ COMPLETE — Create frontend Deployment manifest — Must
- [x] **003-backend-deployment** ✅ COMPLETE — Create backend Deployment manifest — Must
- [x] **004-postgresql-statefulset** ✅ COMPLETE — Create PostgreSQL StatefulSet manifest — Must
- [x] **005-minio-statefulset** ✅ COMPLETE — Create MinIO StatefulSet manifest — Must
- [x] **006-rabbitmq-statefulset** ✅ COMPLETE — Create RabbitMQ StatefulSet manifest — Must
- [x] **007-celery-deployment** ✅ COMPLETE — Create Celery worker Deployment manifest — Must
- [x] **008-service-definitions** ✅ COMPLETE — Create Service manifests for all services — Must
- [x] **009-ingress-configuration** ✅ COMPLETE — Configure Ingress controller and routing — Must
- [x] **010-secrets-template** ✅ COMPLETE — Create k8s Secrets template — Must
- [x] **011-configmaps** ✅ COMPLETE — Create ConfigMaps for environment variables — Must
- [x] **012-liveness-probes** ✅ COMPLETE — Implement liveness probes (all services) — Must
- [x] **013-readiness-probes** ✅ COMPLETE — Implement readiness probes (all services) — Must
- [x] **014-resource-limits** ✅ COMPLETE — Define resource requests and limits — Must
- [x] **015-rbac-policies** ✅ COMPLETE — Implement RBAC policies and service accounts — Must
- [x] **016-manifest-validation** ✅ COMPLETE — Validate manifests (kubectl validate) — Must
- [x] **017-dry-run-deployment** ✅ COMPLETE — Test dry-run deployment — Should
- [x] **018-deployment-docs** ✅ COMPLETE — Document manifest deployment procedure — Should

#### Unit: 005-db-migrations

- [x] **001-review-alembic** ✅ COMPLETE — Review current Alembic setup in backend — Must
- [x] **002-migration-job** ✅ COMPLETE — Design k8s Job template for Alembic migrations — Must
- [x] **003-migration-validation** ✅ COMPLETE — Implement pre-deployment migration validation — Must
- [x] **004-migration-dryrun** ✅ COMPLETE — Create migration dry-run mechanism — Must
- [x] **005-rollback-procedure** ✅ COMPLETE — Create migration rollback procedure — Must
- [x] **006-test-success** ✅ COMPLETE — Test migration success (happy path) — Must
- [x] **007-test-failure** ✅ COMPLETE — Test migration failure and recovery — Must
- [x] **008-zero-downtime** ✅ COMPLETE — Validate zero-downtime migration approach — Must
- [x] **009-migration-guide** ✅ COMPLETE — Document migration best practices — Should
- [x] **010-troubleshooting** ✅ COMPLETE — Create migration troubleshooting guide — Should

#### Unit: 006-ci-cd-pipeline

- [x] **001-workflow-structure** ✅ COMPLETE — Design GitHub Actions workflow structure — Must
- [x] **002-pr-workflow** ✅ COMPLETE — Create PR workflow (build + test trigger) — Must
- [x] **003-docker-build** ✅ COMPLETE — Configure Docker image build — Must
- [x] **004-unit-tests** ✅ COMPLETE — Implement unit test execution — Must
- [x] **005-push-registry** ✅ COMPLETE — Push images to private registry — Must
- [x] **006-staging-workflow** ✅ COMPLETE — Create staging deployment workflow — Must
- [x] **007-health-check-validation** ✅ COMPLETE — Implement health check validation — Must
- [x] **008-github-oidc** ✅ COMPLETE — Configure GitHub OIDC for k8s access — Must
- [x] **009-notifications** ✅ COMPLETE — Add deployment notifications (Slack/email) — Should
- [x] **010-branch-protection** ✅ COMPLETE — Create branch protection rules — Should
- [x] **011-rollback-trigger** ✅ COMPLETE — Implement rollback trigger mechanism — Should
- [x] **012-e2e-test** ✅ COMPLETE — Test end-to-end CI/CD pipeline — Must
- [x] **013-workflow-docs** ✅ COMPLETE — Document CI/CD workflows and troubleshooting — Should

#### Unit: 007-observability-recovery

- [x] **001-log-aggregation** ✅ COMPLETE — Configure kubectl log aggregation and export — Must
- [x] **002-structured-logging-fe** ✅ COMPLETE — Implement structured logging (request IDs) in frontend — Must
- [x] **003-structured-logging-be** ✅ COMPLETE — Implement structured logging (request IDs) in backend — Must
- [x] **004-pod-alerting** ✅ COMPLETE — Configure pod crash alerting — Must
- [x] **005-node-alerting** ✅ COMPLETE — Configure node failure alerting — Must
- [x] **006-rollout-procedure** ✅ COMPLETE — Document kubectl rollout undo procedure — Must
- [x] **007-test-rollout** ✅ COMPLETE — Test rollout undo scenario — Must
- [x] **008-restore-procedure** ✅ COMPLETE — Document database restore procedure from backup — Must
- [x] **009-test-restore** ✅ COMPLETE — Test database restore procedure — Must

---

## Stories by Status

- **Completed**: 167 (all intents 001-007)
- **Planned/Generated**: 0
- **Draft (new)**: 0
- **In Progress**: 0

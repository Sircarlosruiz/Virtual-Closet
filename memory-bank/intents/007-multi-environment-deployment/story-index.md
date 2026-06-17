---
intent: 007-multi-environment-deployment
created: 2026-06-17T14:50:00Z
total_stories: 42
---

# Story Index: Multi-Environment Deployment Strategy

## Unit 1: Dev Environment Setup (7 stories)

| ID | Title | Priority | Status |
|---|---|---|---|
| 001-refactor-docker-compose | Refactor docker-compose.yml | Must | Draft |
| 002-configure-alembic-auto | Configure Alembic auto-migration on startup | Must | Draft |
| 003-hot-reload-frontend | Enable hot-reload for frontend development | Must | Draft |
| 004-hot-reload-backend | Enable hot-reload for backend development | Must | Draft |
| 005-env-example | Create and document .env.example template | Must | Draft |
| 006-test-dev-startup | Test full development environment startup | Must | Draft |
| 007-dev-guide | Document local development quick-start guide | Should | Draft |

## Unit 2: Infrastructure Provisioning (12 stories)

| ID | Title | Priority | Status |
|---|---|---|---|
| 001-terraform-structure | Design Terraform project structure for hcloud | Must | Draft |
| 002-terraform-variables | Create Terraform variables and outputs | Must | Draft |
| 003-hcloud-vpc | Provision Hetzner VPC and networking | Must | Draft |
| 004-k3s-control-plane | Provision CX21 control plane node with k3s | Must | Draft |
| 005-k3s-worker | Provision CX31 worker node with k3s | Must | Draft |
| 006-node-configuration | Configure node labels and taints | Must | Draft |
| 007-persistent-volumes | Implement persistent volume provisioning | Must | Draft |
| 008-backup-cronjob | Create PostgreSQL backup cronjob | Must | Draft |
| 009-test-backup | Test backup creation and storage | Must | Draft |
| 010-test-restore | Test restore procedure from backup | Must | Draft |
| 011-ops-documentation | Document cluster management procedures | Should | Draft |
| 012-terraform-state | Implement Terraform remote state backend | Should | Draft |

## Unit 3: Container Optimization (12 stories)

| ID | Title | Priority | Status |
|---|---|---|---|
| 001-analyze-dockerfile | Analyze current Dockerfile or create new | Must | Draft |
| 002-frontend-docker | Design frontend Dockerfile with multi-stage build | Must | Draft |
| 003-backend-docker | Design backend Dockerfile with multi-stage build | Must | Draft |
| 004-frontend-health | Implement /health endpoint in frontend | Must | Draft |
| 005-backend-health | Implement /health endpoint in backend | Must | Draft |
| 006-health-check-instruction | Add HEALTHCHECK instruction to Dockerfiles | Must | Draft |
| 007-nonroot-user | Create non-root user configuration | Must | Draft |
| 008-optimize-layers | Optimize image layers and dependencies | Must | Draft |
| 009-build-documentation | Document build process and optimization techniques | Must | Draft |
| 010-test-images | Test image builds and validate sizes | Must | Draft |
| 011-security-scan | Run security scan on images (Trivy) | Must | Draft |
| 012-push-to-registry | Push images to registry and validate pull | Should | Draft |

## Unit 4: Kubernetes Deployment Configuration (18 stories)

| ID | Title | Priority | Status |
|---|---|---|---|
| 001-manifest-structure | Design k8s manifest folder structure | Must | Draft |
| 002-frontend-deployment | Create frontend Deployment manifest | Must | Draft |
| 003-backend-deployment | Create backend Deployment manifest | Must | Draft |
| 004-postgresql-statefulset | Create PostgreSQL StatefulSet manifest | Must | Draft |
| 005-minio-statefulset | Create MinIO StatefulSet manifest | Must | Draft |
| 006-rabbitmq-statefulset | Create RabbitMQ StatefulSet manifest | Must | Draft |
| 007-celery-deployment | Create Celery worker Deployment manifest | Must | Draft |
| 008-service-definitions | Create Service manifests for all services | Must | Draft |
| 009-ingress-configuration | Configure Ingress controller and routing | Must | Draft |
| 010-secrets-template | Create k8s Secrets template | Must | Draft |
| 011-configmaps | Create ConfigMaps for environment variables | Must | Draft |
| 012-liveness-probes | Implement liveness probes (all services) | Must | Draft |
| 013-readiness-probes | Implement readiness probes (all services) | Must | Draft |
| 014-resource-limits | Define resource requests and limits | Must | Draft |
| 015-rbac-policies | Implement RBAC policies and service accounts | Must | Draft |
| 016-manifest-validation | Validate manifests (kubectl validate) | Must | Draft |
| 017-dry-run-deployment | Test dry-run deployment | Should | Draft |
| 018-deployment-docs | Document manifest deployment procedure | Should | Draft |

## Unit 5: Database Migrations & Management (10 stories)

| ID | Title | Priority | Status |
|---|---|---|---|
| 001-review-alembic | Review current Alembic setup in backend | Must | Draft |
| 002-migration-job | Design k8s Job template for Alembic migrations | Must | Draft |
| 003-migration-validation | Implement pre-deployment migration validation | Must | Draft |
| 004-migration-dryrun | Create migration dry-run mechanism | Must | Draft |
| 005-rollback-procedure | Create migration rollback procedure | Must | Draft |
| 006-test-success | Test migration success (happy path) | Must | Draft |
| 007-test-failure | Test migration failure and recovery | Must | Draft |
| 008-zero-downtime | Validate zero-downtime migration approach | Must | Draft |
| 009-migration-guide | Document migration best practices | Should | Draft |
| 010-troubleshooting | Create migration troubleshooting guide | Should | Draft |

## Unit 6: CI/CD Pipeline Automation (13 stories)

| ID | Title | Priority | Status |
|---|---|---|---|
| 001-workflow-structure | Design GitHub Actions workflow structure | Must | Draft |
| 002-pr-workflow | Create PR workflow (build + test trigger) | Must | Draft |
| 003-docker-build | Configure Docker image build | Must | Draft |
| 004-unit-tests | Implement unit test execution | Must | Draft |
| 005-push-registry | Push images to private registry | Must | Draft |
| 006-staging-workflow | Create staging deployment workflow | Must | Draft |
| 007-health-check-validation | Implement health check validation | Must | Draft |
| 008-github-oidc | Configure GitHub OIDC for k8s access | Must | Draft |
| 009-notifications | Add deployment notifications (Slack/email) | Should | Draft |
| 010-branch-protection | Create branch protection rules | Should | Draft |
| 011-rollback-trigger | Implement rollback trigger mechanism | Should | Draft |
| 012-e2e-test | Test end-to-end CI/CD pipeline | Must | Draft |
| 013-workflow-docs | Document CI/CD workflows and troubleshooting | Should | Draft |

## Unit 7: Observability & Disaster Recovery (9 stories)

| ID | Title | Priority | Status |
|---|---|---|---|
| 001-log-aggregation | Configure kubectl log aggregation and export | Must | Draft |
| 002-structured-logging-fe | Implement structured logging (request IDs) in frontend | Must | Draft |
| 003-structured-logging-be | Implement structured logging (request IDs) in backend | Must | Draft |
| 004-pod-alerting | Configure pod crash alerting | Must | Draft |
| 005-node-alerting | Configure node failure alerting | Must | Draft |
| 006-rollout-procedure | Document kubectl rollout undo procedure | Must | Draft |
| 007-test-rollout | Test rollout undo scenario | Must | Draft |
| 008-restore-procedure | Document database restore procedure from backup | Must | Draft |
| 009-test-restore | Test database restore procedure | Must | Draft |

---

## Summary

| Unit | Stories | Complexity | Priority |
|------|---------|-----------|----------|
| 1: Dev Environment | 7 | M | High |
| 2: Infrastructure | 12 | L | High |
| 3: Containers | 12 | M | High |
| 4: k8s Config | 18 | L | High |
| 5: DB Migrations | 10 | M | High |
| 6: CI/CD | 13 | L | High |
| 7: Observability | 9 | M | Medium |
| **TOTAL** | **42** | **XL** | - |

**Must-Have Stories**: 38  
**Should-Have Stories**: 4  
**Could-Have Stories**: 0

---

## Dependency Map

```
Unit 1 (Dev) ────┐
                 ├──> Unit 4 (k8s) ───┐
Unit 2 (Infra) ──┤                     ├──> Unit 6 (CI/CD) ──> Unit 7 (Observability)
                 ├──> Unit 5 (DB) ────┤
Unit 3 (Container)┘
```

---

## Status Legend

- **Draft**: Story written, needs review (Checkpoint 3)
- **Ready**: Reviewed, ready for bolt planning (Checkpoint 3)
- **In Progress**: Being implemented in bolt
- **Implemented**: Code complete
- **Done**: All acceptance criteria met

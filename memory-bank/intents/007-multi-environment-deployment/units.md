---
intent: 007-multi-environment-deployment
phase: inception
status: units-decomposed
created: 2026-06-17T14:40:00Z
updated: 2026-06-17T14:40:00Z
---

# Multi-Environment Deployment Strategy — Unit Decomposition

## Units Overview

This intent decomposes into **7 independent but interdependent units** covering infrastructure provisioning, container optimization, Kubernetes manifests, CI/CD automation, and disaster recovery.

---

## Unit 1: Development Environment Setup

**Description**: Refactor and optimize docker-compose.yml for local development with all required services, removing obsolete components (catvton) and supporting GPU-enabled AI models.

**Assigned Requirements**:
- FR-1: Development Environment (Docker Compose)

**Responsibilities**:
- Clean up docker-compose.yml (remove catvton_cache, unused services)
- Ensure all services start via single `docker-compose up`
- Configure database migrations to auto-run on startup
- Enable hot-reload for Next.js frontend and FastAPI backend
- Support GPU inference for fashn/flux models (local development)
- Document .env setup for local development

**Stories**:
- Refactor docker-compose.yml structure
- Remove catvton service and related volumes
- Configure Alembic auto-migration on startup
- Add hot-reload for frontend development
- Add hot-reload for backend development
- Document .env.example for local development
- Validate GPU support for AI models (optional)

**Deliverables**:
- Refactored docker-compose.yml
- .env.example (gitignored template)
- Local development guide

**Dependencies**:
- Depends on: None (foundation)
- Depended by: None directly (used in parallel with other units)

**Estimated Complexity**: M (refactoring + validation)

---

## Unit 2: Infrastructure Provisioning (Terraform + Hetzner k3s)

**Description**: Provision multi-node k3s cluster on Hetzner using Terraform + hcloud, configure networking, storage, and backup infrastructure. Implement PostgreSQL backup automation to Hetzner Object Storage.

**Assigned Requirements**:
- FR-2: Staging k3s Cluster Infrastructure (Terraform + Hetzner)
- FR-8: Backup Strategy (PostgreSQL & MinIO)

**Responsibilities**:
- Design and implement Terraform configurations for Hetzner infrastructure
- Provision 2-node k3s cluster: CX21 (control plane), CX31 (workers + stateful)
- Configure networking, firewalls, and node labels
- Set up persistent volume provisioning (local-path-provisioner or similar)
- Implement backup automation: daily pg_dump cronjob → Hetzner Object Storage
- Document cluster scaling strategy for future expansion

**Stories**:
- Design Terraform module structure for hcloud
- Implement Hetzner VPC and networking configuration
- Provision control plane node (CX21) with k3s
- Provision worker node (CX31) with k3s
- Configure persistent volume provisioning
- Implement PostgreSQL backup cronjob
- Document cluster management and scaling procedures
- Test restore procedure from backups

**Deliverables**:
- Terraform modules (hcloud, k3s configuration)
- Networking configuration (VPC, firewalls, node labels)
- Backup automation scripts and cronjobs
- Cluster documentation and runbooks
- Terraform state management strategy

**Dependencies**:
- Depends on: None (foundation)
- Depended by: Unit 4 (Kubernetes Deployment Configuration), Unit 6 (CI/CD Pipeline)

**Estimated Complexity**: L (complex infrastructure automation)

---

## Unit 3: Container Optimization & Multi-Stage Builds

**Description**: Create optimized Dockerfile configurations for Next.js 14 (frontend) and FastAPI (backend) with security hardening, multi-stage builds, and embedded health checks.

**Assigned Requirements**:
- FR-3: Container Image Optimization & Multi-Stage Builds

**Responsibilities**:
- Create multi-stage Dockerfile for frontend (Next.js 14)
- Create multi-stage Dockerfile for backend (FastAPI)
- Implement health check endpoints in Dockerfiles
- Use optimized base images (alpine/slim variants)
- Implement security hardening: non-root user, minimal attack surface
- Document image size optimization and build process
- Set up image build reproducibility

**Stories**:
- Design frontend Dockerfile with multi-stage build
- Design backend Dockerfile with multi-stage build
- Implement /health endpoints in both services
- Add health check instructions to Dockerfiles
- Create non-root user for container execution
- Optimize image layers and dependencies
- Test image build process and sizes
- Document build process and push to registry

**Deliverables**:
- Optimized Dockerfile for frontend
- Optimized Dockerfile for backend
- Health check endpoint implementations
- Build documentation and scripts

**Dependencies**:
- Depends on: None
- Depended by: Unit 4 (Kubernetes Deployment Configuration), Unit 6 (CI/CD Pipeline)

**Estimated Complexity**: M (image optimization + hardening)

---

## Unit 4: Kubernetes Deployment Configuration

**Description**: Create Kubernetes manifests for all services (frontend, backend, PostgreSQL, MinIO, RabbitMQ, Celery worker) with proper pod configuration, networking, storage, secrets management, and health probes.

**Assigned Requirements**:
- FR-4: Kubernetes Manifests & Deployments
- FR-6: Secrets & Configuration Management
- FR-7: Health Checks, Liveness & Readiness Probes

**Responsibilities**:
- Design k8s manifest structure (Deployments, StatefulSets, Services, Ingress)
- Create Deployment for frontend (2+ replicas, rolling updates)
- Create Deployment for backend (2+ replicas, rolling updates)
- Create StatefulSet for PostgreSQL with persistent volumes
- Create StatefulSet for MinIO with persistent volumes
- Create StatefulSet for RabbitMQ with persistent volumes
- Create Deployment for Celery worker with auto-scaling configuration
- Configure liveness and readiness probes for all services
- Implement k8s Secrets for credentials and API keys
- Implement ConfigMaps for environment-specific configuration
- Configure Ingress controller for external access
- Define resource requests/limits for all pods
- Implement RBAC with minimal service account permissions

**Stories**:
- Design k8s manifest architecture and folder structure
- Create frontend Deployment with 2+ replicas
- Create backend Deployment with 2+ replicas
- Create PostgreSQL StatefulSet with persistent volume
- Create MinIO StatefulSet with persistent volume
- Create RabbitMQ StatefulSet with persistent volume
- Create Celery worker Deployment with auto-scaling hints
- Implement Ingress controller and routing rules
- Create k8s Secrets for sensitive data
- Create ConfigMaps for environment variables
- Configure liveness and readiness probes for all services
- Define resource requests and limits per pod
- Implement RBAC and service account policies
- Test manifest deployment and pod health

**Deliverables**:
- Kubernetes manifest files (YAML)
- Ingress configuration
- Secret and ConfigMap templates
- Health check implementations
- RBAC policies

**Dependencies**:
- Depends on: Unit 2 (Infrastructure), Unit 3 (Container Optimization)
- Depended by: Unit 6 (CI/CD Pipeline)

**Estimated Complexity**: L (comprehensive manifests + configuration)

---

## Unit 5: Database Migrations & Management

**Description**: Implement automated database schema migration strategy using Alembic in k8s environments, ensuring zero-downtime migrations and reliable rollback procedures.

**Assigned Requirements**:
- FR-5: Database Migrations & Init Strategy

**Responsibilities**:
- Configure Alembic for PostgreSQL schema management
- Design k8s Job for automated migration execution on deployment
- Implement pre-deployment validation of migrations
- Create migration rollback procedures
- Ensure backward-compatible schema changes (zero-downtime)
- Test migration scenarios (success, failure, rollback)
- Document migration process and best practices

**Stories**:
- Review current Alembic configuration in backend
- Design k8s Job template for migration execution
- Implement pre-deployment migration validation
- Create migration rollback procedure
- Test migration success scenario
- Test migration failure and rollback
- Document migration best practices
- Create migration troubleshooting guide

**Deliverables**:
- k8s Job manifest for Alembic migrations
- Migration validation script
- Migration rollback procedures
- Migration documentation and runbooks

**Dependencies**:
- Depends on: Unit 2 (Infrastructure), Unit 4 (Kubernetes Configuration)
- Depended by: Unit 6 (CI/CD Pipeline)

**Estimated Complexity**: M (migration automation + testing)

---

## Unit 6: CI/CD Pipeline Automation (GitHub Actions)

**Description**: Design and implement GitHub Actions workflows for automated building, testing, and staging deployment. Include health check validation and deployment feedback mechanisms.

**Assigned Requirements**:
- FR-9: CI/CD Pipeline (GitHub Actions)

**Responsibilities**:
- Create GitHub Actions workflow for build and test on PR/push
- Configure Docker image build and push to private registry
- Implement unit test execution before image build
- Create deployment workflow for staging on main branch merge
- Implement health check validation before deployment completion
- Add deployment feedback (logs, status, rollback options)
- Configure GitHub OIDC for secure k8s cluster access
- Set up branch protection rules

**Stories**:
- Design GitHub Actions workflow structure
- Create build and test workflow for PRs
- Configure Docker image build and registry push
- Implement unit test execution
- Create staging deployment workflow
- Implement health check validation
- Configure GitHub OIDC for k8s access
- Add deployment notifications and logs
- Test end-to-end CI/CD pipeline
- Document CI/CD workflows

**Deliverables**:
- GitHub Actions workflow files (.github/workflows/)
- Build and test scripts
- Deployment scripts
- Health check validation scripts
- GitHub OIDC configuration
- CI/CD documentation

**Dependencies**:
- Depends on: Unit 2 (Infrastructure), Unit 3 (Container Optimization), Unit 4 (Kubernetes Configuration), Unit 5 (Database Migrations)
- Depended by: None (final integration)

**Estimated Complexity**: L (multi-step workflow + integrations)

---

## Unit 7: Observability & Disaster Recovery

**Description**: Implement logging aggregation, basic monitoring, health check systems, and disaster recovery procedures including rollback and restore capabilities.

**Assigned Requirements**:
- FR-10: Logging & Basic Observability
- FR-11: Rollback & Disaster Recovery

**Responsibilities**:
- Configure kubectl log aggregation and export
- Implement structured logging in applications (request IDs, tracing)
- Set up basic alerting for critical failures (pod crashes, node offline)
- Document rollback procedures using `kubectl rollout undo`
- Test rollback scenarios
- Create database restore procedure from backups
- Document disaster recovery playbooks
- Plan Phase 2 observability (Prometheus + Grafana)

**Stories**:
- Configure kubectl log aggregation
- Implement request ID tracing in frontend/backend
- Set up pod crash alerting
- Set up node failure alerting
- Test kubectl rollout undo procedure
- Test database restore from backup
- Create disaster recovery runbook
- Document observability Phase 2 requirements
- Test end-to-end disaster recovery scenario

**Deliverables**:
- Log aggregation configuration
- Structured logging implementation
- Alert configuration (basic)
- Rollback procedures and scripts
- Database restore procedure
- Disaster recovery runbooks
- Phase 2 observability plan (Prometheus + Grafana scope)

**Dependencies**:
- Depends on: Unit 2 (Infrastructure), Unit 4 (Kubernetes Configuration), Unit 6 (CI/CD Pipeline)
- Depended by: None (integrates all)

**Estimated Complexity**: M (logging + recovery procedures)

---

## Unit Dependency Graph

```
                        Unit 1: Dev Environment
                                (standalone)

Unit 2: Infrastructure ────────┐
(k3s + Backups)                │
        │                       │
        ├──> Unit 3: Container  │
        │    Optimization       │
        │         │             │
        │         └──> Unit 4: K8s Manifests ───┐
        │              (+ Secrets + Probes)      │
        │                       │                │
        └──────────────────────> Unit 5: DB ────┤
                        Migrations              │
                                                │
                                   ┌────────────┘
                                   │
                            Unit 6: CI/CD ───────> (Final Integration)
                            (GitHub Actions)
                                   │
                                   │
                            Unit 7: Observability
                            & Disaster Recovery
```

## Execution Order

Based on dependencies and criticality:

| Phase | Units | Timeline | Notes |
|-------|-------|----------|-------|
| **Phase 1: Foundation** | Unit 1, Unit 2 | Week 1-2 | Dev env + infrastructure setup |
| **Phase 2: Containerization** | Unit 3 | Week 2 | Docker image optimization (parallel) |
| **Phase 3: k8s Configuration** | Unit 4, Unit 5 | Week 2-3 | Manifests + DB automation (parallel) |
| **Phase 4: CI/CD Integration** | Unit 6 | Week 3 | GitHub Actions automation |
| **Phase 5: Operational Readiness** | Unit 7 | Week 3-4 | Observability + recovery procedures |

**Parallel Execution Opportunities**:
- Unit 1 (dev) and Unit 2 (infrastructure) can proceed in parallel
- Unit 3 (containers) can proceed in parallel with Unit 2
- Unit 4 (manifests) and Unit 5 (migrations) can proceed in parallel
- Unit 6 (CI/CD) requires all previous units

## Cross-Unit Dependencies Summary

| Unit | Depends On | Is Depended By |
|------|-----------|----------------|
| 1: Dev | None | None |
| 2: Infrastructure | None | 4, 5, 6, 7 |
| 3: Containers | None | 4, 6 |
| 4: k8s Manifests | 2, 3 | 6, 7 |
| 5: DB Migrations | 2, 4 | 6 |
| 6: CI/CD | 2, 3, 4, 5 | 7 |
| 7: Observability | 2, 4, 6 | None |

---

## Unit Complexity Summary

| Unit | Complexity | Effort Estimate |
|------|-----------|-----------------|
| 1: Dev Environment | M | 3-5 days |
| 2: Infrastructure | L | 5-8 days |
| 3: Containers | M | 2-4 days |
| 4: k8s Manifests | L | 5-7 days |
| 5: DB Migrations | M | 2-3 days |
| 6: CI/CD | L | 4-6 days |
| 7: Observability | M | 3-4 days |
| **TOTAL** | **XL** | **~25-35 days** |

---

## Notes

- **MVP Timeline**: 3-4 weeks aligns with parallel execution of units 1-3, then 4-5, then 6-7
- **Quality Gates**: Each unit includes testing and validation stories
- **Documentation**: Each unit includes runbooks and operational procedures
- **Phase 2 Deferral**: Prometheus+Grafana observability documented in Unit 7 for Phase 2 implementation

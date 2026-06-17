---
intent: 007-multi-environment-deployment
phase: inception
status: draft
created: 2026-06-17T14:30:00Z
updated: 2026-06-17T14:30:00Z
---

# Requirements: Multi-Environment Deployment Strategy

## Intent Overview

Design and implement a comprehensive deployment strategy for Virtual Closet across multiple environments (dev, staging, production) using Docker Compose for development and k3s for production on Hetzner. Establish CI/CD pipelines, database migration strategies, and rollback procedures to ensure reliable releases.

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Reduce deployment time | From manual setup to < 15 min automated deployment | Must |
| Minimize downtime on releases | Zero-downtime deployments using health checks and gradual rollouts | Must |
| Enable staging validation | Full staging environment mirrors production for pre-release testing | Must |
| Automated rollback capability | Rollback any failed deployment within 5 minutes | Should |
| Multi-tenancy support in deployment | Separate namespaces/resources per tenant in k3s | Should |

---

## Functional Requirements

### FR-1: Development Environment (Docker Compose)
- **Description**: Refactor docker-compose.yml to separate development (with local GPU support) from production, removing unused services (catvton) and optimizing for local development
- **Acceptance Criteria**: 
  - Single `docker-compose up` starts all dev services (frontend, backend, PostgreSQL, MinIO, RabbitMQ, Celery worker)
  - Database migrations auto-run on startup via Alembic
  - Hot-reload enabled for frontend and backend code
  - Volumes properly configured to persist data between restarts
  - catvton_cache volume removed (service replaced by Replicate in production)
  - .env files (gitignored) manage local secrets and credentials
  - GPU support for fashn/flux models available for local development
- **Priority**: Must
- **Related Stories**: To be defined

### FR-2: Staging k3s Cluster Infrastructure (Terraform + Hetzner)
- **Description**: Provision multi-node k3s cluster on Hetzner with Terraform/hcloud automation
- **Acceptance Criteria**:
  - Terraform configuration provisions 2-node cluster: CX21 (control plane + frontend/backend), CX31 (workers + stateful services)
  - k3s cluster initialized and healthy
  - Network policies and node labels configured for service placement
  - Persistent Volume storage provisioned for PostgreSQL and MinIO (using local-path-provisioner or similar)
  - Terraform state secured and documented
  - Scaling playbook documented for future expansion
- **Priority**: Must
- **Related Stories**: To be defined

### FR-3: Container Image Optimization & Multi-Stage Builds
- **Description**: Create optimized Dockerfile configurations for frontend (Next.js 14) and backend (FastAPI) for k8s deployment
- **Acceptance Criteria**:
  - Multi-stage Dockerfiles reduce image size and attack surface
  - Health check endpoints defined in Dockerfiles (HEALTHCHECK instruction)
  - Images built from optimized base images (e.g., node:20-alpine, python:3.11-slim)
  - Build process documented and reproducible
  - Images runnable with non-root user for security
- **Priority**: Must
- **Related Stories**: To be defined

### FR-4: Kubernetes Manifests & Deployments
- **Description**: Create k8s manifests for all services (frontend, backend, PostgreSQL, MinIO, RabbitMQ, Celery) running on staging cluster
- **Acceptance Criteria**:
  - Deployments for frontend (Next.js) with 2+ replicas
  - Deployments for backend (FastAPI) with 2+ replicas
  - StatefulSet for PostgreSQL with persistent volume and backups
  - StatefulSet or Deployment for MinIO with persistent volume
  - StatefulSet for RabbitMQ with persistent volume
  - Deployment for Celery worker with auto-scaling based on queue depth
  - Resource requests/limits defined for all pods
  - Service and Ingress objects configured for routing
- **Priority**: Must
- **Related Stories**: To be defined

### FR-5: Database Migrations & Init Strategy
- **Description**: Automated database schema migration strategy using Alembic in k8s
- **Acceptance Criteria**:
  - Alembic migrations run automatically via k8s Job on each deployment
  - Migrations are reversible and tested before deployment
  - Zero-downtime migrations (backward-compatible schema changes)
  - Migration status tracked and logged
  - Rollback procedure for failed migrations documented
- **Priority**: Must
- **Related Stories**: To be defined

### FR-6: Secrets & Configuration Management
- **Description**: Secure handling of secrets and environment-specific configuration using k8s Secrets
- **Acceptance Criteria**:
  - All secrets (DB passwords, API keys, JWT secrets, etc.) stored in k8s Secrets
  - Secrets never committed to git
  - CI/CD pipeline creates secrets from GitHub Actions environment variables
  - Local dev setup uses .env files (gitignored) injected via Docker Compose
  - Staging and production secret separation implemented
  - ConfigMaps used for non-sensitive environment configuration
- **Priority**: Must
- **Related Stories**: To be defined

### FR-7: Health Checks, Liveness & Readiness Probes
- **Description**: Implement health checks for all services to enable k8s self-healing and traffic routing
- **Acceptance Criteria**:
  - Liveness probes detect hung services and trigger restarts
  - Readiness probes prevent traffic routing to starting pods
  - Frontend: HTTP /health endpoint, probe every 10s, timeout 5s
  - Backend: HTTP /health endpoint, probe every 10s, timeout 5s
  - Database: Query-based readiness probe
  - RabbitMQ & MinIO: HTTP probes configured
  - Celery worker: Custom readiness script checking worker health
- **Priority**: Must
- **Related Stories**: To be defined

### FR-8: Backup Strategy (PostgreSQL & MinIO)
- **Description**: Automated daily backups to Hetzner Object Storage ($0.023/GB)
- **Acceptance Criteria**:
  - Daily pg_dump cronjob runs on schedule (e.g., 2 AM UTC)
  - Backups uploaded to Hetzner Object Storage (S3-compatible)
  - Backup retention policy: 30 days
  - Restore procedure documented and tested
  - MinIO data persistence via StatefulSet volumes (no separate backup for MVP)
  - Backup monitoring and alerting (basic kubectl logs check)
- **Priority**: Must
- **Related Stories**: To be defined

### FR-9: CI/CD Pipeline (GitHub Actions)
- **Description**: Automated build, test, and staging deployment via GitHub Actions
- **Acceptance Criteria**:
  - Frontend and backend build triggered on PR and main branch pushes
  - Unit tests run before image build
  - Images pushed to private registry (Docker Hub or equivalent)
  - Staging deployment triggered automatically on main branch merge
  - Health checks validate pod readiness before marking deployment complete
  - Rollback manual approval gate before production (future)
- **Priority**: Must
- **Related Stories**: To be defined

### FR-10: Logging & Basic Observability
- **Description**: Centralized logging and basic monitoring for staging environment
- **Acceptance Criteria**:
  - kubectl logs accessible and searchable (via aggregator like Loki, or basic log export)
  - Application logs include request IDs for tracing
  - Infrastructure metrics monitored: pod CPU/memory, node disk usage
  - Basic alerting for critical failures (pod crashes, node offline)
  - Prometheus + Grafana planned for Phase 2 (Sprint 4+)
- **Priority**: Should
- **Related Stories**: To be defined

### FR-11: Rollback & Disaster Recovery
- **Description**: Quick rollback capability for failed deployments
- **Acceptance Criteria**:
  - Previous k8s deployment versions retained (default k8s behavior)
  - Rollback via single kubectl rollout undo command
  - Estimated rollback time < 5 minutes
  - Database rollback procedure for failed migrations documented
  - Restore from backup procedure documented and tested
- **Priority**: Should
- **Related Stories**: To be defined

---

## Non-Functional Requirements

### Performance
| Requirement | Metric | Target |
|-------------|--------|--------|
| Deployment duration | End-to-end time (build → deploy → ready) | < 15 minutes |
| Container startup time | Time from image pull to liveness probe pass | < 30 seconds |
| Database migration duration | Time to Alembic migrations completion | < 5 minutes |
| Pod initialization | Time from pod creation to readiness | < 45 seconds |

### Scalability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Frontend replicas | Minimum in staging/prod | 2 replicas (1 per node) |
| Backend replicas | Minimum in staging/prod | 2 replicas (1 per node) |
| Resource requests | Frontend pod | 500m CPU, 512Mi memory |
| Resource requests | Backend pod | 1000m CPU, 1Gi memory |
| Database StatefulSet | PostgreSQL replicas | 1 primary (future: HA with standby) |
| Auto-scaling | Horizontal scaling trigger | Manual for MVP; auto-scaling documented for Phase 2 |

### Reliability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Availability | Staging uptime SLA | 99% (2.4 hours downtime/month acceptable) |
| Deployment success rate | Non-failing releases | > 95% |
| Recovery time | RTO for failed pod | < 2 minutes (automatic restart) |
| Recovery time | RTO for node failure | < 5 minutes (pod rescheduling) |
| Data recovery time | RPO for database | < 24 hours (daily backup) |
| Liveness probe recovery | Time to restart hung pod | < 45 seconds |

### Security
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Secrets encryption | k8s Secrets at rest + TLS in transit | Default k8s behavior |
| Image repository | Private Docker registry | Private repo (Docker Hub or equivalent) |
| Pod security | Non-root container user | All images run as non-root |
| Network policies | Pod-to-pod communication isolated | Ingress controller manages external access |
| RBAC | Service account permissions | Minimal: frontend/backend service accounts, admin for cluster setup |
| Secrets rotation | Manual rotation process | Documented procedure for quarterly rotation |

### Compliance & Data Governance
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Data residency | Hetzner Germany datacenter (EU) | Staging in EU region (eu-de) |
| Backup retention | 30-day rolling backup archive | Daily backups, automated deletion after 30 days |
| Backup testing | Restore procedure tested | Monthly restore validation |
| Data access logging | Audit logs for secrets access | Deferred to Phase 2 (kubectl audit logs sufficient for MVP) |

---

## Constraints

### Technical Constraints
- **k3s Cluster Topology**: 2-node multi-node cluster on Hetzner (CX21 + CX31)
  - Node 1 (CX21): Control plane + Frontend/Backend deployments
  - Node 2 (CX31): Worker nodes + Stateful services (PostgreSQL, RabbitMQ, MinIO)
- **PostgreSQL version**: 16 (current) as StatefulSet, no managed database service
- **Container runtime**: containerd (default in k3s)
- **Database backups**: PostgreSQL pg_dump → Hetzner Object Storage ($0.023/GB), no external backup service
- **AI/ML services**: 
  - Development: fashn/flux models run locally with GPU support (docker-compose)
  - Production: Replicate provider (no local GPU inference in k8s)
  - catvton service removed from production manifests
- **No HashiCorp Vault**: Use k8s Secrets native for MVP (cost/complexity optimization)
- **Secrets provisioning**: GitHub Actions creates k8s Secrets from GitHub Actions env vars
- **Development environment**: Keep docker-compose.yml with local GPU support, separate from k8s production configs
- **Network**: Ingress controller required for external access to frontend/API

### Business Constraints
- **Timeline**: MVP planning/preparation done in this intent (3-4 weeks from start). Actual cluster provisioning follows once services validated.
- **Cost optimization**: Minimize Hetzner resource usage; prefer StatefulSets over managed services where cost-effective
- **Team capacity**: DevOps/infra work prioritized after application services stabilized
- **Scope boundaries**: This intent covers planning, container prep, and manifests. Actual cluster provisioning execution deferred.

---

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| Hetzner account and API credentials available | Cannot provision infrastructure | Validate Hetzner API token before Terraform execution |
| Terraform + hcloud can automate cluster provisioning | Manual cluster setup is error-prone | Reference tested hcloud Terraform modules (e.g., kube-hetzner community) |
| PostgreSQL and MinIO can run as StatefulSets in k8s | Data loss or corruption | Use persistent volumes, test backup/restore before production |
| Next.js 14 builds and runs in container without GPU | Runtime issues with SSR | Test build and deployment in isolated container |
| FastAPI health checks can be implemented without major refactoring | Deployment failures due to missing probes | Minimal code changes; add /health endpoint |
| GitHub Actions can securely manage secrets and deploy to k8s | Credential leaks or unauthorized deployments | Use GitHub OIDC + RBAC for cluster access |
| Hetzner Object Storage (S3-compatible) available for backups | Backup failures | Confirm S3 API access, test upload/download |
| CI/CD pipeline can validate deployments and auto-rollback on failure | Failed deployments remain stuck in bad state | Implement health check validation before declaring success |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Which Terraform hcloud modules should we reference? (e.g., kube-hetzner) | DevOps Lead | [TBD] | Pending |
| Should we use Hetzner Cloud Load Balancer or k8s Ingress? | DevOps Lead | [TBD] | Pending |
| What's the exact Hetzner Object Storage bucket structure for backups? | DevOps Lead | [TBD] | Pending |
| Should GitHub Actions use OIDC or API token for k8s cluster access? | DevOps Lead | [TBD] | Pending |
| How frequently should we test backup restore procedures? | Operations | [TBD] | Pending (Recommend: monthly) |
| What monitoring/alerting tools will replace Prometheus+Grafana before Phase 2? | DevOps Lead | [TBD] | Pending (kubectl logs sufficient for MVP) |

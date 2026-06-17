---
id: 039-kubernetes-config
unit: 004-kubernetes-deployment-config
intent: 007-multi-environment-deployment
type: ddd-construction-bolt
status: planned
stories:
  - 001-manifest-structure
  - 002-frontend-deployment
  - 003-backend-deployment
  - 004-postgresql-statefulset
  - 005-minio-statefulset
  - 006-rabbitmq-statefulset
  - 007-celery-deployment
  - 008-service-definitions
  - 009-ingress-configuration
  - 010-secrets-template
  - 011-configmaps
  - 012-liveness-probes
  - 013-readiness-probes
  - 014-resource-limits
  - 015-rbac-policies
  - 016-manifest-validation
  - 017-dry-run-deployment
  - 018-deployment-docs
created: 2026-06-17T15:05:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts:
  - 037-infrastructure
  - 038-containers
enables_bolts:
  - 040-ci-cd-pipeline
requires_units: []
blocks: false

complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 3
---

# Bolt: 039-kubernetes-config

## Overview

Create comprehensive Kubernetes manifests for all Virtual Closet services (frontend, backend, PostgreSQL, MinIO, RabbitMQ, Celery) with proper networking, secrets, health probes, resource management, and RBAC. This is the core deployment configuration for staging and production.

## Objective

Define complete Kubernetes manifests that enable reliable, scalable deployment of Virtual Closet on k3s cluster with proper observability, security, and resource management.

## Stories Included

- **001-manifest-structure**: Folder organization (Must)
- **002-frontend-deployment**: Frontend Deployment (Must)
- **003-backend-deployment**: Backend Deployment (Must)
- **004-postgresql-statefulset**: PostgreSQL StatefulSet (Must)
- **005-minio-statefulset**: MinIO StatefulSet (Must)
- **006-rabbitmq-statefulset**: RabbitMQ StatefulSet (Must)
- **007-celery-deployment**: Celery worker Deployment (Must)
- **008-service-definitions**: Service definitions (Must)
- **009-ingress-configuration**: Ingress configuration (Must)
- **010-secrets-template**: Secrets template (Must)
- **011-configmaps**: ConfigMaps (Must)
- **012-liveness-probes**: Liveness probes (Must)
- **013-readiness-probes**: Readiness probes (Must)
- **014-resource-limits**: Resource requests/limits (Must)
- **015-rbac-policies**: RBAC policies (Must)
- **016-manifest-validation**: Manifest validation (Must)
- **017-dry-run-deployment**: Dry-run testing (Should)
- **018-deployment-docs**: Documentation (Should)

## Bolt Type

**Type**: DDD Construction Bolt  
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Model**: k8s architecture, service topology → bolt-039-01-domain-model.md
- [ ] **2. Design**: Manifest structure, probe strategy, resource sizing → bolt-039-02-technical-design.md
- [ ] **3. Implement**: Manifest YAML files, Ingress config, RBAC
- [ ] **4. Test**: Validation, dry-run, documentation → bolt-039-03-test-report.md

## Dependencies

### Requires
- Bolt 037: Infrastructure (cluster must be operational)
- Bolt 038: Containers (images must be ready)

### Enables
- Bolt 040: CI/CD pipeline (depends on manifests for deployment)

## Success Criteria

- [ ] All manifest files created and organized
- [ ] Frontend Deployment (2+ replicas)
- [ ] Backend Deployment (2+ replicas)
- [ ] PostgreSQL StatefulSet with PVC
- [ ] MinIO StatefulSet with PVC
- [ ] RabbitMQ StatefulSet with PVC
- [ ] Celery worker Deployment
- [ ] Service definitions for all services
- [ ] Ingress controller configured
- [ ] Secrets template created
- [ ] ConfigMaps created
- [ ] Liveness probes on all services
- [ ] Readiness probes on all services
- [ ] Resource limits defined
- [ ] RBAC policies implemented
- [ ] Manifests validated
- [ ] Dry-run successful
- [ ] Documentation complete
- [ ] All tests passing
- [ ] Code reviewed and merged

## Complexity Assessment

- **Complexity**: High (18 stories, multiple services, probes, RBAC)
- **Uncertainty**: Medium (k8s probe tuning, resource sizing)
- **Dependencies**: Medium (depends on infrastructure and images)
- **Testing Scope**: E2E (full manifest validation, dry-run)

## Implementation Notes

- Create namespace for staging (e.g., `virtual-closet-staging`)
- Use StatefulSets for stateful services (PostgreSQL, MinIO, RabbitMQ)
- Probe timeouts: liveness 10s, readiness 5s
- Resource requests conservative initially, adjust post-deployment
- RBAC follows least-privilege principle
- Secrets template for CI/CD to populate
- Document all manifest assumptions

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Pod resource limits too low | Monitor usage, adjust limits incrementally |
| Readiness probes failing | Tune timeouts based on actual startup time |
| StatefulSet data loss | PV backup/recovery tested before production |
| RBAC too restrictive | Test permissions for each service account |

## Owner & Timeline

**Assigned To**: DevOps Engineer (k8s expertise)  
**Estimated Duration**: 5-7 days  
**Target Start**: Week 2 (after Bolts 037, 038 complete)  
**Critical Path Item**: YES

## Definition of Done

- [ ] All 18 stories completed
- [ ] All manifests valid (kubectl validate)
- [ ] Dry-run successful
- [ ] Pod probes tested and working
- [ ] RBAC verified
- [ ] Secrets template ready for CI/CD
- [ ] Documentation complete
- [ ] No critical issues in code review
- [ ] Merged to dev branch

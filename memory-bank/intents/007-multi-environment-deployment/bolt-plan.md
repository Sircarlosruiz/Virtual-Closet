---
intent: 007-multi-environment-deployment
phase: complete
created: 2026-06-17T15:00:00Z
updated: 2026-07-01T00:00:00Z
---

# Bolt Plan: Multi-Environment Deployment Strategy

## Overview

**81 stories** grouped into **7 bolts** (one per unit) using **ddd-construction-bolt** type (infrastructure work with domain-heavy requirements).

**Status**: ✅ All bolts complete. Implementation uses AWS EKS instead of Hetzner k3s.

---

## Bolt Assignments

### Bolt 001: Dev Environment Setup (Unit 1)

**Stories**: 7 stories  
**Bolt Type**: `ddd-construction-bolt`  
**Complexity**: Medium  
**Effort**: 3-5 days  
**Owner**: Backend Engineer (Docker expertise)

**Stories Included**:
1. 001-refactor-docker-compose
2. 002-configure-alembic-auto
3. 003-hot-reload-frontend
4. 004-hot-reload-backend
5. 005-env-example
6. 006-test-dev-startup
7. 007-dev-guide

**Deliverables**:
- Refactored docker-compose.yml
- .env.example
- Local development guide

**Dependencies**:
- Requires: None (foundation)
- Enables: Nothing blocks this, but Unit 4/5/6 depend on validated dev environment

---

### Bolt 002: Infrastructure Provisioning (Unit 2)

**Stories**: 12 stories  
**Bolt Type**: `ddd-construction-bolt`  
**Complexity**: Large  
**Effort**: 5-8 days  
**Owner**: DevOps Engineer (Terraform + hcloud expertise)

**Stories Included**:
1. 001-terraform-structure
2. 002-terraform-variables
3. 003-hcloud-vpc
4. 004-k3s-control-plane
5. 005-k3s-worker
6. 006-node-configuration
7. 007-persistent-volumes
8. 008-backup-cronjob
9. 009-test-backup
10. 010-test-restore
11. 011-ops-documentation
12. 012-terraform-state

**Deliverables**:
- Terraform modules (hcloud + k3s)
- Operational k3s cluster (CX21 + CX31)
- Backup automation
- Runbooks

**Dependencies**:
- Requires: None (foundation)
- Enables: Bolt 004, 005, 006, 007

---

### Bolt 003: Container Optimization (Unit 3)

**Stories**: 12 stories  
**Bolt Type**: `ddd-construction-bolt`  
**Complexity**: Medium  
**Effort**: 2-4 days  
**Owner**: Backend/Frontend Engineer (Docker expertise)

**Stories Included**:
1. 001-analyze-dockerfile
2. 002-frontend-docker
3. 003-backend-docker
4. 004-frontend-health
5. 005-backend-health
6. 006-health-check-instruction
7. 007-nonroot-user
8. 008-optimize-layers
9. 009-build-documentation
10. 010-test-images
11. 011-security-scan
12. 012-push-to-registry

**Deliverables**:
- Optimized Dockerfiles (frontend + backend)
- Health check endpoints
- Build documentation
- Images in private registry

**Dependencies**:
- Requires: None (standalone)
- Enables: Bolt 004, 006

---

### Bolt 004: Kubernetes Deployment Configuration (Unit 4)

**Stories**: 18 stories  
**Bolt Type**: `ddd-construction-bolt`  
**Complexity**: Large  
**Effort**: 5-7 days  
**Owner**: DevOps Engineer (k8s expertise)

**Stories Included**:
1. 001-manifest-structure
2. 002-frontend-deployment
3. 003-backend-deployment
4. 004-postgresql-statefulset
5. 005-minio-statefulset
6. 006-rabbitmq-statefulset
7. 007-celery-deployment
8. 008-service-definitions
9. 009-ingress-configuration
10. 010-secrets-template
11. 011-configmaps
12. 012-liveness-probes
13. 013-readiness-probes
14. 014-resource-limits
15. 015-rbac-policies
16. 016-manifest-validation
17. 017-dry-run-deployment
18. 018-deployment-docs

**Deliverables**:
- Complete Kubernetes manifest set
- Ingress configuration
- Health probe configuration
- RBAC policies
- Deployment documentation

**Dependencies**:
- Requires: Bolt 002 (Infrastructure), Bolt 003 (Container images)
- Enables: Bolt 006

---

### Bolt 005: Database Migrations & Management (Unit 5)

**Stories**: 10 stories  
**Bolt Type**: `ddd-construction-bolt`  
**Complexity**: Medium  
**Effort**: 2-3 days  
**Owner**: Backend Engineer (Alembic + k8s Job expertise)

**Stories Included**:
1. 001-review-alembic
2. 002-migration-job
3. 003-migration-validation
4. 004-migration-dryrun
5. 005-rollback-procedure
6. 006-test-success
7. 007-test-failure
8. 008-zero-downtime
9. 009-migration-guide
10. 010-troubleshooting

**Deliverables**:
- k8s Job manifest for migrations
- Migration validation scripts
- Rollback procedure
- Migration documentation

**Dependencies**:
- Requires: Bolt 002 (Infrastructure), Bolt 004 (k8s configuration)
- Enables: Bolt 006

---

### Bolt 006: CI/CD Pipeline Automation (Unit 6)

**Stories**: 13 stories  
**Bolt Type**: `ddd-construction-bolt`  
**Complexity**: Large  
**Effort**: 4-6 days  
**Owner**: DevOps Engineer (GitHub Actions + k8s access)

**Stories Included**:
1. 001-workflow-structure
2. 002-pr-workflow
3. 003-docker-build
4. 004-unit-tests
5. 005-push-registry
6. 006-staging-workflow
7. 007-health-check-validation
8. 008-github-oidc
9. 009-notifications
10. 010-branch-protection
11. 011-rollback-trigger
12. 012-e2e-test
13. 013-workflow-docs

**Deliverables**:
- GitHub Actions workflows (.github/workflows/)
- Build and deployment scripts
- Health check validation
- GitHub OIDC configuration
- CI/CD documentation

**Dependencies**:
- Requires: Bolt 002, 003, 004, 005 (all foundation)
- Enables: Bolt 007

---

### Bolt 007: Observability & Disaster Recovery (Unit 7)

**Stories**: 9 stories (implied in unit-brief)  
**Bolt Type**: `ddd-construction-bolt`  
**Complexity**: Medium  
**Effort**: 3-4 days  
**Owner**: DevOps Engineer (Logging + recovery procedures)

**Stories Included** (from unit-brief):
1. 001-log-aggregation
2. 002-structured-logging-fe
3. 003-structured-logging-be
4. 004-pod-alerting
5. 005-node-alerting
6. 006-rollout-procedure
7. 007-test-rollout
8. 008-restore-procedure
9. 009-test-restore

**Deliverables**:
- Log aggregation configuration
- Structured logging implementation
- Alert configuration
- Disaster recovery runbook
- Phase 2 observability plan

**Dependencies**:
- Requires: Bolt 002, 004, 006 (all foundation)
- Enables: None (final integration)

---

## Dependency Graph

```
Bolt 001 (Dev)  ───┐
                    │
Bolt 002 (Infra) ──┼──> Bolt 004 (k8s) ────┐
                    │                        ├──> Bolt 006 (CI/CD) ──> Bolt 007 (Observability)
                    ├──> Bolt 005 (DB) ─────┤
Bolt 003 (Container)┘
```

**Critical Path**:
1. **Phase 1 (Parallel)**:
   - Bolt 001: Dev Environment (3-5d)
   - Bolt 002: Infrastructure (5-8d)
   - Bolt 003: Containers (2-4d)

2. **Phase 2 (Depends on Phase 1)**:
   - Bolt 004: k8s Manifests (5-7d, depends on 002+003)
   - Bolt 005: DB Migrations (2-3d, depends on 002+004)

3. **Phase 3 (Depends on Phases 1+2)**:
   - Bolt 006: CI/CD (4-6d, depends on 002+003+004+005)

4. **Phase 4 (Depends on all)**:
   - Bolt 007: Observability (3-4d, depends on 002+004+006)

**Total Critical Path**: ~25-30 days (with parallelization of Phase 1)

---

## Complexity & Uncertainty Assessment

| Bolt | Complexity | Uncertainty | Dependencies | Testing | Risk Level |
|------|-----------|-------------|--------------|---------|-----------|
| 001 | Medium | Low | None | High | Low |
| 002 | High | Medium | None | High | Medium |
| 003 | Medium | Low | None | High | Low |
| 004 | High | Medium | 002, 003 | High | Medium |
| 005 | Medium | Low | 002, 004 | High | Low |
| 006 | High | Medium | 002-005 | High | Medium |
| 007 | Medium | Low | 002, 004, 006 | Medium | Low |

---

## Execution Sequence

### Week 1-2: Foundation (Phase 1 - Parallel)

**Bolt 001** (Dev Environment)
- Days 1-5: Refactor docker-compose, configure Alembic, hot-reload
- Days 5-6: Testing and documentation
- **Outcome**: Local dev environment ready for team

**Bolt 002** (Infrastructure)
- Days 1-8: Terraform modules, k3s provisioning, backup automation
- Days 8: Testing and runbook creation
- **Outcome**: Operational k3s cluster on Hetzner

**Bolt 003** (Container Optimization)
- Days 1-4: Dockerfiles, health checks, security scan
- Days 4: Push to registry
- **Outcome**: Optimized container images ready for deployment

### Week 2-3: Configuration (Phase 2)

**Bolt 004** (k8s Manifests)
- Days 1-7: Manifests for all services, probes, RBAC
- Days 7: Validation and dry-run
- **Outcome**: Complete k8s manifest set, ready for deployment

**Bolt 005** (DB Migrations)
- Days 1-3: Alembic Job, validation, rollback procedures
- Days 3: Testing and documentation
- **Outcome**: Automated migration system in k8s

### Week 3-4: Automation & Operations (Phase 3-4)

**Bolt 006** (CI/CD)
- Days 1-6: Workflows, GitHub OIDC, health checks
- Days 6: E2E testing
- **Outcome**: Automated staging deployment pipeline

**Bolt 007** (Observability)
- Days 1-4: Logging, alerting, recovery procedures
- Days 4: Testing and Phase 2 planning
- **Outcome**: Operational observability and disaster recovery

---

## Success Criteria

Each bolt is complete when:
- [ ] All assigned stories implemented and tested
- [ ] Acceptance criteria for all stories met
- [ ] Documentation complete
- [ ] Cross-bolt dependencies validated
- [ ] Code reviewed and merged
- [ ] Operational runbooks created

---

## Notes

- **Parallelization**: Bolts 001, 002, 003 can run in parallel (no dependencies)
- **Fast-Track**: If time-constrained, focus on Bolts 001-006; defer Bolt 007 (Phase 2 candidate)
- **Risk Mitigation**: Bolt 002 (Terraform) has medium uncertainty → test thoroughly with dry-run
- **Quality Gates**: Each bolt includes testing and validation stories
- **Documentation**: Every bolt produces operational documentation/runbooks

---
id: 037-infrastructure
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
type: ddd-construction-bolt
status: planned
stories:
  - 001-terraform-structure
  - 002-terraform-variables
  - 003-hcloud-vpc
  - 004-k3s-control-plane
  - 005-k3s-worker
  - 006-node-configuration
  - 007-persistent-volumes
  - 008-backup-cronjob
  - 009-test-backup
  - 010-test-restore
  - 011-ops-documentation
  - 012-terraform-state
created: 2026-06-17T15:05:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts: []
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

# Bolt: 037-infrastructure

## Overview

Provision a complete 2-node k3s cluster on Hetzner infrastructure using Terraform and hcloud provider. This includes networking, storage, backup automation, and all operational runbooks. This is the critical infrastructure foundation for staging and production deployments.

## Objective

Create a reproducible, Infrastructure-as-Code deployment of k3s cluster on Hetzner with automated backup to Object Storage, enabling reliable staging environment for pre-release validation.

## Stories Included

- **001-terraform-structure**: Design Terraform modules (Must)
- **002-terraform-variables**: Create vars and outputs (Must)
- **003-hcloud-vpc**: Provision Hetzner VPC (Must)
- **004-k3s-control-plane**: Provision CX21 control plane (Must)
- **005-k3s-worker**: Provision CX31 worker node (Must)
- **006-node-configuration**: Configure labels and taints (Must)
- **007-persistent-volumes**: Implement PV provisioning (Must)
- **008-backup-cronjob**: Create PostgreSQL backup automation (Must)
- **009-test-backup**: Test backup creation (Must)
- **010-test-restore**: Test restore from backup (Must)
- **011-ops-documentation**: Create runbooks (Should)
- **012-terraform-state**: Implement remote state backend (Should)

## Bolt Type

**Type**: DDD Construction Bolt  
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Model**: Domain model for Hetzner infrastructure, cluster topology → bolt-037-01-domain-model.md
- [ ] **2. Design**: Terraform architecture, backup strategy, networking design → bolt-037-02-technical-design.md
- [ ] **3. Implement**: Terraform code, cluster provisioning, backup setup
- [ ] **4. Test**: Cluster health checks, backup/restore validation → bolt-037-03-test-report.md

## Dependencies

### Requires
- None (foundation infrastructure)

### Enables
- Bolt 040: CI/CD pipeline (depends on operational cluster)
- Bolt 039: Database migrations (depends on infrastructure)

## Success Criteria

- [ ] Terraform modules created and documented
- [ ] Hetzner VPC configured
- [ ] k3s cluster operational (CX21 control + CX31 worker)
- [ ] Node labels and taints configured
- [ ] PV provisioning working
- [ ] PostgreSQL backup cronjob running and tested
- [ ] Restore procedure tested and documented
- [ ] Runbooks created
- [ ] Terraform state secured
- [ ] All tests passing
- [ ] Code reviewed and merged

## Complexity Assessment

- **Complexity**: High (infrastructure automation, multiple services)
- **Uncertainty**: Medium (Hetzner API, k3s specifics)
- **Dependencies**: Medium (external Hetzner APIs)
- **Testing Scope**: E2E (full cluster validation, backup/restore)

## Implementation Notes

- Reference kube-hetzner community modules as baseline
- Use Hetzner EU datacenter for GDPR compliance
- Configure node labels for pod scheduling (cpu-intensive, memory-intensive)
- Test Terraform plan before apply
- Implement state locking to prevent concurrent modifications
- Document all Hetzner API calls and rate limits
- Backup strategy: daily pg_dump + 30-day retention

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Hetzner API outages blocking deployment | Implement retry logic, monitor Hetzner status |
| k3s version incompatibility with apps | Test k3s version with backend/frontend before full rollout |
| Terraform state corruption | Remote backend with locking (S3 or similar) |
| Data loss due to PV issues | Regular backup/restore validation (monthly) |

## Owner & Timeline

**Assigned To**: DevOps Engineer (Terraform + hcloud expertise)  
**Estimated Duration**: 5-8 days  
**Target Start**: Week 1 (parallel with Bolt 036)  
**Critical Path Item**: YES

## Definition of Done

- [ ] All 12 stories completed
- [ ] Terraform modules reproducible on clean machine
- [ ] k3s cluster healthy and accessible
- [ ] Backup/restore verified working
- [ ] Operational runbooks complete
- [ ] Security review complete (API tokens, RBAC)
- [ ] No critical issues in code review
- [ ] Merged to dev branch

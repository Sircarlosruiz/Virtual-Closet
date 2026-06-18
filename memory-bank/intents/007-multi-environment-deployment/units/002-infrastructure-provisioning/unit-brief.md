---
unit: 002-infrastructure-provisioning
unit_type: infrastructure
default_bolt_type: ddd-construction-bolt
intent: 007-multi-environment-deployment
created: 2026-06-17T14:42:00.000Z
status: complete
---

# Unit Brief: Infrastructure Provisioning (Terraform + Hetzner k3s)

## Purpose

Provision multi-node k3s cluster on Hetzner using Terraform + hcloud, configure networking, storage, and implement backup automation to Hetzner Object Storage.

## Scope

**In Scope**:
- Terraform modules for Hetzner infrastructure (hcloud provider)
- 2-node k3s cluster: CX21 (control plane), CX31 (workers + stateful)
- VPC networking, firewalls, node labeling
- Persistent volume provisioning (local-path-provisioner)
- PostgreSQL backup automation (daily pg_dump → Hetzner Object Storage)
- Cluster scaling documentation
- Terraform state management

**Out of Scope**:
- Kubernetes manifests (Unit 4)
- Application configuration
- Monitoring infrastructure (Phase 2)

## Key Decisions

1. **Multi-Node**: 2-node cluster for staging (cost-effective, supports HA patterns)
2. **No Managed DB**: PostgreSQL runs in StatefulSet (cost savings: ~€15/month)
3. **Terraform**: Infrastructure as Code for reproducibility
4. **Backup to Object Storage**: Daily backups, 30-day retention (€0.023/GB)

## Acceptance Criteria

- [ ] Terraform modules created for hcloud
- [ ] VPC and networking configured
- [ ] CX21 control plane node provisioned and healthy
- [ ] CX31 worker node provisioned and healthy
- [ ] k3s cluster healthy and accessible via kubectl
- [ ] Persistent volume provisioning working
- [ ] PostgreSQL backup cronjob operational
- [ ] Backup restore procedure tested
- [ ] Cluster scaling documentation complete
- [ ] Terraform state secured (remote state backend)

## Stories

1. Design Terraform project structure for hcloud
2. Create Terraform variables and outputs
3. Provision Hetzner VPC and networking
4. Provision CX21 control plane node with k3s
5. Provision CX31 worker node with k3s
6. Configure node labels and taints
7. Implement persistent volume provisioning
8. Create PostgreSQL backup cronjob
9. Test backup creation and storage
10. Test restore procedure from backup
11. Document cluster management procedures
12. Implement Terraform remote state backend

## Deliverables

- Terraform modules (VPC, k3s cluster, backup automation)
- k3s cluster (operational on Hetzner)
- Networking configuration (firewalls, node labels)
- Backup automation (scripts, cronjobs)
- Operational runbooks and documentation
- Terraform state (secured)

## Dependencies

- Depends on: None (foundation)
- Depended by: Unit 4 (k8s Manifests), Unit 5 (DB Migrations), Unit 6 (CI/CD), Unit 7 (Observability)

## Effort Estimate

**5-8 days** (infrastructure automation + testing + documentation)

## Risk Factors

- Risk: Hetzner API changes or outages
  - Mitigation: Use stable hcloud provider version, monitor Hetzner status
- Risk: k3s version incompatibility with applications
  - Mitigation: Test with target k3s version before full rollout
- Risk: Terraform state corruption
  - Mitigation: Use remote backend (S3 or equivalent) with state locking

## Notes

- Scaling strategy documented for easy expansion (add more CX31 nodes)
- Cost monitoring required (daily pg_dump costs, storage usage)
- Backup restore procedure must be tested monthly

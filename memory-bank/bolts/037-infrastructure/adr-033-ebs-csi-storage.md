# ADR-033: EBS CSI Driver for Persistent Storage

## Status
Accepted (replaces local-path-provisioner on k3s)

## Context
EKS nodes need persistent storage for StatefulSets (PostgreSQL, MinIO, RabbitMQ). The previous approach used local-path-provisioner (built into k3s) which stored data on node-local disks.

## Decision
Use **AWS EBS (Elastic Block Store) gp3 volumes** via the **EBS CSI Driver** for all persistent storage.

### Configuration
- **Storage class**: `gp2` (EKS default, backed by gp3)
- **EBS CSI Driver**: Installed via Helm chart (v2.30.0)
- **Volume type**: gp3 (general purpose SSD)
- **Encryption**: EBS default encryption enabled

## Consequences

### Positive
- Volumes are network-attached — survive node replacement
- EBS snapshots for backup (integrated with AWS Backup)
- No data locality constraints — pods can schedule on any node
- IOPS and throughput configurable per volume
- Managed by AWS — no storage provisioning scripts

### Negative
- EBS volumes cost more than local disk (~$0.08/GB/month for gp3)
- EBS is AZ-scoped — PVCs bound in one AZ can't attach to nodes in another
- Requires EBS CSI driver installation and maintenance

### Mitigations
- Node group spans 2 AZs; StatefulSets pin to specific AZ via topology
- EBS gp3 provides 3000 IOPS baseline — sufficient for staging

## Supersedes
Previous decision to use local-path-provisioner on self-managed k3s.

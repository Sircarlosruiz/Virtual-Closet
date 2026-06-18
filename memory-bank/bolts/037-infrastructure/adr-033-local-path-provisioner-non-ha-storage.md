---
bolt: 037-infrastructure
created: 2026-06-17T17:30:00Z
status: accepted
superseded_by: null
---

# ADR-033: local-path-provisioner for PVs (Non-HA Node-Local Storage)

## Context

StatefulSets in the cluster (PostgreSQL, Redis, MinIO, RabbitMQ) require PersistentVolumes. Several storage approaches are available for a 2-node k3s cluster:

1. **local-path-provisioner** (k3s built-in): Creates PVs from the host node's local filesystem. Simple, zero cost, zero setup. Not replicated — single node failure makes the volume inaccessible.
2. **Longhorn** (Hetzner-compatible distributed storage): Replicates volumes across nodes. Provides HA storage — node failure is transparent to pods. Adds ~1-2 GB RAM overhead per node, requires 2+ replicas.
3. **Hetzner CSI driver**: Provisions Hetzner block storage volumes (€0.048/GB/month) and attaches them to nodes. Volume survives node destruction (not just failure). Hetzner block volumes are detachable and re-attachable.
4. **NFS on control-plane**: Shared storage via NFS from the control-plane. Simple but control-plane becomes a storage dependency.

The cluster currently has a single worker node (CX31) where all stateful workloads run.

## Decision

Use **k3s built-in local-path-provisioner** for all PersistentVolumes in the initial staging cluster. Accept the non-HA characteristic. Compensate with daily pg_dump backups to Hetzner Object Storage.

## Rationale

At 2-node scale (1 worker), distributed storage provides no benefit — Longhorn replication requires at least 2 healthy nodes for a replica count of 2. With 1 worker node, Longhorn would store only 1 replica anyway, providing the same durability as local-path.

- **local-path-provisioner** is zero-cost, zero-overhead, and already installed by k3s — no additional setup or RAM overhead
- Application data (PostgreSQL) is protected by daily pg_dump backups — the real data durability story
- MinIO data (garment images, generated VTON images) can be re-generated or re-uploaded; loss is inconvenient but not catastrophic
- Redis data is ephemeral (session denylist, OTP state with TTLs) — loss is safe; services degrade gracefully
- RabbitMQ data (queued messages) — loss on node failure means in-flight VTON jobs need re-submission; acceptable at staging scale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------------|
| Longhorn | HA storage, volume replication | ~1-2 GB RAM per node; no benefit with 1 worker (can't replicate); operational complexity | No actual HA benefit at 1-worker scale |
| Hetzner CSI driver | Volume survives node destruction; detachable | €0.048/GB/month (~€3.50/mo for 73GB total); volume attach/detach adds pod startup latency | Cost + complexity not justified; backup provides equivalent recovery story |
| NFS from control-plane | Simple shared storage | Control-plane becomes storage dependency; performance worse than local disk; control-plane is CX21 (smaller disk) | Unacceptable coupling; performance concern |

## Consequences

### Positive

- Zero setup — local-path-provisioner is active by default in k3s
- Zero additional cost
- No RAM overhead on nodes
- Full local disk performance (no network I/O for storage)
- Simple to understand and debug

### Negative

- **Single worker failure** → all StatefulSet volumes inaccessible until worker recovers. PostgreSQL, Redis, MinIO, RabbitMQ all stop. Application goes offline.
- **Worker disk failure** → data loss for all volumes not covered by backup. PostgreSQL is covered (daily pg_dump). MinIO is partially covered (garment originals are safe; generated images may need regeneration).
- PVs are bound to the worker node via `nodeAffinity` — scaling to a second worker does not automatically migrate or balance volumes

### Risks

- **Risk**: CX31 disk fails → PostgreSQL data lost since last backup (up to 24 hours). **Mitigation**: Daily pg_dump backups; alert on backup failure; consider increasing backup frequency to 6h for production.
- **Risk**: Team adds a second worker, moves a StatefulSet, and the PV can't follow. **Mitigation**: Document that PVs are node-local; StatefulSet migration requires manual data migration or restore from backup; see ops runbook.
- **Risk**: MinIO data (generated VTON images) lost on disk failure — not covered by pg_dump. **Mitigation**: MinIO data is regeneratable (re-run VTON job); document recovery procedure. For production, evaluate Hetzner CSI for MinIO specifically.

## Related

- **Stories**: 007-persistent-volumes, 008-backup-cronjob, 009-test-backup, 010-test-restore
- **Standards**: If the cluster scales beyond 2 worker nodes, re-evaluate this decision — Longhorn or Hetzner CSI becomes viable
- **Previous ADRs**: ADR-032 (self-managed k3s — this decision is predicated on k3s and its built-in provisioner)

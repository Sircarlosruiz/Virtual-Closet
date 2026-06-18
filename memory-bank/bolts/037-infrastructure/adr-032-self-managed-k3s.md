---
bolt: 037-infrastructure
created: 2026-06-17T17:30:00Z
status: accepted
superseded_by: null
---

# ADR-032: Self-Managed k3s Over Hetzner Managed Kubernetes

## Context

The platform requires a Kubernetes cluster for staging and production workloads. Two options exist on Hetzner:

1. **Hetzner Managed Kubernetes (MKE)**: Fully managed control plane, automatic upgrades, SLA-backed API availability. Additional cost: ~€120/month for the managed control-plane fee, on top of node costs.
2. **Self-managed k3s**: Install and operate the Kubernetes distribution ourselves on Hetzner VMs. No managed fee; we own the control plane.

The decision has downstream impact on: cluster upgrade procedures, control-plane availability SLA, operational runbook complexity, and total infrastructure cost.

## Decision

Use **self-managed k3s** on Hetzner VMs provisioned via Terraform.

## Rationale

At the current scale (staging + small production), the operational cost of self-managing k3s is acceptable and the cost savings are material:

- **Cost**: CX21 control-plane (~€4/mo) vs Hetzner MKE control-plane fee (~€120/mo) — saving ~€116/month (~€1,400/year)
- **k3s simplicity**: k3s is a certified, lightweight Kubernetes distribution maintained by SUSE/Rancher; it bundles containerd, flannel, CoreDNS, local-path-provisioner, and Traefik — zero additional components to install
- **Upgrade control**: We pin the k3s version explicitly (`k3s_version` Terraform variable) and upgrade intentionally; managed services sometimes force upgrades on their own schedule
- **GDPR**: k3s control-plane runs entirely on our EU VMs; no control-plane data leaves Hetzner EU

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------------|
| Hetzner Managed Kubernetes | Managed upgrades, API SLA, less ops burden | ~€120/mo extra; upgrade schedule partially managed by Hetzner | Cost not justified at current scale |
| AWS EKS / GKE | Battle-tested, rich ecosystem | Major cost increase; GDPR data residency complexity; vendor lock-in | Out of scope for Hetzner-first strategy |
| Docker Compose on single server | Simplest possible | No Kubernetes primitives (rolling updates, health checks, resource limits, HPA) | Insufficient for multi-service staged deployment |

## Consequences

### Positive

- ~€116/month cost saving vs Hetzner MKE
- Full control over k3s version and upgrade timing
- Control-plane data stays on our EU VMs (GDPR clean)
- k3s is certified Kubernetes — standard `kubectl` and manifests work unchanged
- Local-path-provisioner, CoreDNS, and flannel included — minimal setup

### Negative

- We own control-plane availability: if the CX21 server fails, `kubectl` is unavailable until it recovers (StatefulSets on the worker continue running — data plane is separate from control plane)
- k3s upgrades are a manual Terraform operation (change `k3s_version` variable → `terraform apply`)
- etcd (embedded in k3s) backup is not automatic — control-plane data loss on CX21 disk failure requires cluster rebuild from Terraform (application data safe via pg_dump backups)
- No multi-master HA control plane at current cluster size (single CX21)

### Risks

- **Risk**: CX21 control-plane server hardware fails → kubectl unavailable, no new pod scheduling. **Mitigation**: Terraform provisions a replacement in <10 minutes; application data is on the worker (CX31) and survives; runbook documented in ops docs.
- **Risk**: k3s upstream breaks compatibility with our manifests on major version bump. **Mitigation**: Version pinned; upgrade only on explicit decision; tested in staging before production.

## Related

- **Stories**: 004-k3s-control-plane, 005-k3s-worker, 011-ops-documentation
- **Standards**: Establishes infrastructure provider standard (Hetzner + k3s); should be referenced when evaluating future infrastructure changes
- **Previous ADRs**: ADR-030 (Alembic migration as k8s Job in production — depends on this cluster existing)

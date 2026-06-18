---
adr: 038
title: "kubeconfig Secret Over GitHub OIDC for Bare-Metal k3s Access"
status: accepted
bolt: 040-ci-cd-pipeline
created: 2026-06-18T17:50:00Z
read_when:
  - Configuring GitHub Actions access to the staging k3s cluster
  - Evaluating whether to adopt GitHub OIDC for k8s authentication
  - Rotating or troubleshooting cluster credentials in CI
  - Planning a migration to a cloud-managed Kubernetes cluster
---

## Context

The staging deployment workflow (`deploy-staging.yaml`) needs to run `kubectl` commands against the k3s cluster on Hetzner. GitHub Actions runners are ephemeral VMs with no pre-existing network trust to the cluster.

Two authentication strategies were considered:

**Option A — GitHub OIDC federation**: GitHub Actions can issue OIDC tokens that are exchanged for short-lived cloud credentials. On AWS/GCP/Azure, these credentials can then be used to authenticate to a cloud-managed Kubernetes cluster (EKS, GKE, AKS) without any stored secrets.

**Option B — kubeconfig secret**: The k3s-generated kubeconfig is base64-encoded and stored as a GitHub Actions environment secret (`KUBE_CONFIG_STAGING`). The workflow decodes it into `~/.kube/config` at runtime.

---

## Problem

GitHub OIDC federation requires an **OIDC token exchange endpoint** on the cloud provider side (e.g., AWS STS, GCP Workload Identity). This endpoint validates the GitHub OIDC token and issues cloud credentials.

The staging cluster is bare-metal k3s on a Hetzner dedicated server. There is no cloud provider, no IAM service, and no webhook to validate GitHub OIDC tokens against. GitHub's OIDC integration for Kubernetes exists only via third-party operators (e.g., `pinnipied`, `dex`) that require additional cluster components and ongoing maintenance overhead.

---

## Decision

Store the k3s kubeconfig as a base64-encoded GitHub Actions **environment secret** named `KUBE_CONFIG_STAGING`, scoped to the `staging` environment.

The workflow decodes it at runtime:
```bash
mkdir -p ~/.kube
echo "${{ secrets.KUBE_CONFIG_STAGING }}" | base64 -d > ~/.kube/config
chmod 600 ~/.kube/config
```

The kubeconfig grants access via a **dedicated ServiceAccount** (not the cluster-admin token), scoped to the `virtual-closet-staging` namespace. That ServiceAccount has only the permissions needed for deployments: `get`, `list`, `create`, `update`, `patch`, `delete` on `Deployments`, `Jobs`, and `Pods` in `virtual-closet-staging`.

**Rotation policy**: Rotate the kubeconfig token quarterly, or immediately on team member departure. The token is scoped to a namespace — a leak does not grant cluster-admin access.

---

## Consequences

**Positive:**
- Zero additional cluster components — works on any k8s distribution
- Setup is a single `kubectl create secret` command; no OIDC operator to maintain
- GitHub environment secrets are encrypted at rest; only accessible to runs targeting the `staging` environment
- Namespace-scoped token limits blast radius of a credential leak

**Negative:**
- Stored long-lived credential — must be rotated manually; no automatic expiry
- A compromised secret grants write access to `virtual-closet-staging` until rotated
- Does not scale cleanly to many environments (each needs its own secret)

**Accepted risk mitigation:**
- Scoped to `virtual-closet-staging` namespace only
- GitHub environment protection prevents the secret from being used in unrelated workflows
- Rotation documented in CI.md; quarterly rotation task added to ops calendar

---

## Alternatives Considered

| Alternative | Rejected because |
|-------------|-----------------|
| GitHub OIDC + k8s Pinniped operator | Requires deploying + maintaining Pinniped on the cluster; adds complexity and failure mode without material security gain at current scale |
| GitHub OIDC + Dex | Same issue; additionally Dex needs persistent storage and LDAP/OAuth2 config |
| Cluster-admin kubeconfig | Blast radius too large; if secret leaks, attacker has full cluster control |
| Self-hosted GitHub Actions runner on the cluster | Runner process runs inside k8s; no external kubeconfig needed. Rejected: increases cluster attack surface; runner compromise = cluster compromise |

## Future Path

When the infrastructure migrates to a cloud-managed Kubernetes service (EKS, GKE, AKS), replace `KUBE_CONFIG_STAGING` with GitHub OIDC federation to the cloud provider's IAM. At that point, no stored secrets are needed for cluster access. This ADR should be revisited at migration time.

## Applies To

- `.github/workflows/deploy-staging.yaml` (deploy job)
- `.github/workflows/rollback-staging.yaml` (rollback job)
- All future environment deployment workflows

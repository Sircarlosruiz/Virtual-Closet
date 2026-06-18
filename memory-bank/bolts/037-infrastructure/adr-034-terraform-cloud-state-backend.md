---
bolt: 037-infrastructure
created: 2026-06-17T17:30:00Z
status: accepted
superseded_by: null
---

# ADR-034: Terraform Cloud as Primary State Backend (Over Hetzner Object Storage)

## Context

Terraform state must not be stored locally — it contains sensitive outputs (kubeconfig, k3s token, Object Storage keys) and must be shared across operators and CI/CD pipelines. Two options were evaluated:

1. **Terraform Cloud** (free tier: 1 organization, unlimited workspaces for small teams): Provides remote state storage with native state locking, version history, secret variable storage, and a run UI. State data is stored on HashiCorp's infrastructure (US-based, not EU).
2. **Hetzner Object Storage** (S3-compatible): Keeps state in EU (GDPR clean). Uses Terraform's `s3` backend with a custom endpoint. **Does not support native state locking** — Terraform's S3 backend locking requires DynamoDB, which Hetzner Object Storage doesn't provide.

Both options are available; the choice involves a GDPR data residency trade-off against operational safety (locking).

## Decision

Use **Terraform Cloud** as the primary state backend for all environments. Use Hetzner Object Storage as the documented fallback if Terraform Cloud is unavailable or the team decides to self-host state.

## Rationale

State locking is the primary driver. Without locking, two concurrent `terraform apply` runs can corrupt the state file, causing infrastructure drift that is expensive to recover from. Terraform Cloud provides this for free.

The GDPR concern is mitigated: Terraform state contains infrastructure metadata (IP addresses, resource IDs) and sensitive outputs (tokens, kubeconfig). None of this is personal user data under GDPR. The actual personal data (PostgreSQL database content, MinIO uploads) stays on Hetzner EU infrastructure and is never in Terraform state.

- **State locking**: Terraform Cloud provides optimistic locking out of the box — concurrent applies are serialized automatically
- **Cost**: Free for teams ≤ 5 users with ≤ 500 managed resources; our cluster is well within limits
- **Auditability**: Terraform Cloud maintains a run history with plan/apply logs — useful for incident review
- **CI/CD integration**: GitHub Actions can authenticate to Terraform Cloud via OIDC (no long-lived API tokens needed)

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------------|
| Hetzner Object Storage (S3 backend) | EU data residency; zero external dependency | No native state locking — concurrent apply risk; DynamoDB not available on Hetzner | Locking is non-negotiable for shared infrastructure |
| Local state | Simplest | Not shareable; lost on developer machine failure; can't be used in CI/CD | Rejected immediately — unacceptable for team/CI use |
| Terraform Enterprise (self-hosted) | Full EU residency + locking | Significant operational overhead; licensing cost | Overkill for current scale |
| GitLab Managed Terraform State | EU GitLab instance provides EU residency + locking | Requires GitLab (we use GitHub); adds GitLab dependency | Wrong vendor for our stack |

## Consequences

### Positive

- Native state locking — concurrent applies are safe
- Free for current team size and resource count
- Run history and audit log built in
- Sensitive variables can be stored in Terraform Cloud (encrypted at rest) — no need for local `.tfvars` files with secrets
- OIDC authentication in CI/CD (no long-lived API tokens)

### Negative

- Terraform state metadata lives outside EU (HashiCorp US infrastructure) — technically acceptable under GDPR (no personal data in state) but worth documenting
- External service dependency — if Terraform Cloud is unavailable, `terraform apply` is blocked (state locked remotely). **Fallback**: documented Hetzner Object Storage backend for emergency use.
- Free tier limits: 500 managed resources per workspace; exceeding requires paid plan (~$20/user/month)

### Risks

- **Risk**: Terraform Cloud outage blocks infrastructure changes during an incident. **Mitigation**: Documented emergency fallback to Hetzner Object Storage S3 backend (manual state migration procedure in ops runbook; requires exclusive access discipline).
- **Risk**: Terraform Cloud account credentials compromised → attacker reads state (contains kubeconfig, tokens). **Mitigation**: Rotate all sensitive outputs immediately on suspected compromise; enable 2FA on Terraform Cloud account; use OIDC in CI instead of API tokens.
- **Risk**: Free tier limit (500 resources) reached as cluster grows. **Mitigation**: Monitor resource count; evaluate paid plan or workspace split when approaching limit.

## Related

- **Stories**: 012-terraform-state, 011-ops-documentation
- **Standards**: All future Terraform-managed infrastructure should use the same Terraform Cloud organization and workspace naming convention (`virtualcloset-{environment}`)
- **Previous ADRs**: ADR-032 (k3s self-managed — this state backend stores the cluster's Terraform state)

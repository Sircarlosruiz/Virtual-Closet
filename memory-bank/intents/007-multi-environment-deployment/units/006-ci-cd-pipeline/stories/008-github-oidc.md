---
id: 008-github-oidc
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 008-GitHub OIDC

## User Story

**As a** devops engineer  
**I want** GitHub OIDC configured for Kubernetes cluster access  
**So that** deployments are secure without long-lived credentials

## Acceptance Criteria

- [ ] **Given** the cluster needs GitHub trust, **When** OIDC is configured, **Then** the OIDC provider is configured in GitHub
- [ ] **Given** GitHub is the identity provider, **When** the cluster validates tokens, **Then** the Kubernetes cluster trusts GitHub OIDC
- [ ] **Given** CI/CD needs cluster access, **When** authentication occurs, **Then** a service account is created for CI/CD
- [ ] **Given** the workflow runs, **When** k8s access is needed, **Then** kubeconfig is generated from the OIDC token
- [ ] **Given** credentials are managed, **When** reviewed, **Then** no static credentials are stored
- [ ] **Given** tokens are issued, **When** they expire, **Then** token expiration is handled automatically

## Technical Notes

- Use `actions/deploy-actions` or configure OIDC manually with cloud provider
- For cloud-hosted k8s (EKS/GKE/AKS), configure the provider's OIDC integration
- Create Kubernetes ServiceAccount with appropriate RBAC (limited to CI/CD namespace)
- Use `azure/login` or `aws-actions/configure-aws-credentials` with OIDC if applicable
- Token lifetime should be minimal (default 1 hour from GitHub)
- No `kubeconfig` stored as secret; generate dynamically from OIDC token

## Dependencies

### Requires
- 007-health-check-validation

### Enables
- 012-e2e-test

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| OIDC token exchange fails | Workflow fails with authentication error; no deployment occurs |
| Token expires mid-deployment | Deployment fails; workflow should request fresh token or fail gracefully |
| Service account permissions are too broad | RBAC audit flags over-permissioned account; scope down to minimum required |
| GitHub OIDC provider URL changes | Trust configuration breaks; monitor for provider URL updates |

## Out of Scope

- Multi-cluster OIDC configuration
- OIDC for non-Kubernetes services
- Certificate-based authentication fallback

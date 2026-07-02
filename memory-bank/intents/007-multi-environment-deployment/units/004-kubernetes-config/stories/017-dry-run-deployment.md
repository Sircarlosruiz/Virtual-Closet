---
id: 017-dry-run-deployment
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: should
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 017-Dry-Run Deployment

## User Story

**As a** devops engineer  
**I want** to test a dry-run deployment  
**So that** I can verify manifests work together before actual deployment

## Acceptance Criteria

- [ ] **Given** all manifests are validated, **When** I run a server-side dry-run, **Then** kubectl apply --dry-run=server succeeds
- [ ] **Given** the dry-run results, **When** I review scheduling, **Then** all pods would be scheduled
- [ ] **Given** the dry-run results, **When** I review conflicts, **Then** there are no resource conflicts
- [ ] **Given** the dry-run results, **When** I review the namespace, **Then** the namespace is created or exists
- [ ] **Given** the dry-run results, **When** I review services, **Then** all services are resolvable
- [ ] **Given** the dry-run is complete, **When** I review documentation, **Then** dry-run results are documented

## Technical Notes

- dry-run=server sends manifests to the API server for full validation including admission controllers
- Requires cluster access; cannot be run offline
- Verifies resource quotas, admission webhooks, and API version compatibility
- Document any warnings or validation errors for resolution before actual deployment

## Dependencies

### Requires
- 016-manifest-validation

### Enables
- 018-deployment-docs

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Cluster does not have required storage class | dry-run=server fails with PVC provisioning error |
| Namespace already exists with conflicting resources | dry-run=server reports conflict; existing resources not overwritten |
| Admission webhook rejects manifest | dry-run=server fails with webhook rejection message |

## Out of Scope

- Actual deployment to a cluster
- Load testing or performance validation
- Chaos engineering or fault injection testing

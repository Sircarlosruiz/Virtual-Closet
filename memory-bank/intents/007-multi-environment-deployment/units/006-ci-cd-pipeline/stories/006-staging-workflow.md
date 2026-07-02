---
id: 006-staging-workflow
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 006-Staging Workflow

## User Story

**As a** devops engineer  
**I want** a staging deployment workflow triggered on main branch merge  
**So that** staging is always up to date

## Acceptance Criteria

- [ ] **Given** code is merged to main, **When** the push event fires, **Then** the workflow triggers on push to main
- [ ] **Given** the workflow starts, **When** the image pull step runs, **Then** latest images are pulled from the registry
- [ ] **Given** images are available, **When** the deploy step runs, **Then** Kubernetes manifests are applied to the staging cluster
- [ ] **Given** manifests are applied, **When** a migration is needed, **Then** a migration Job runs before the main deployment
- [ ] **Given** deployment is applied, **When** rollout is monitored, **Then** the workflow waits for deployment rollout to complete
- [ ] **Given** deployment completes, **When** status is checked, **Then** deployment status is reported

## Technical Notes

- Use `kubectl apply -f` or `kustomize build | kubectl apply -f` for manifest application
- Migration Job should run with `kubectl wait --for=condition=complete`
- Use `kubectl rollout status deployment/<name> --timeout=300s` to wait for rollout
- Set `needs` dependency chain: build → push → deploy
- Use GitHub Environments for staging with optional protection rules

## Dependencies

### Requires
- 005-push-registry

### Enables
- 007-health-check-validation

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Migration Job fails | Deployment is halted; workflow fails with migration error |
| Rollout exceeds timeout | Workflow fails; deployment is marked as failed |
| Image pull fails (registry down) | Workflow fails at pull step with clear error |
| Concurrent deployments to staging | Second deployment waits or is queued via concurrency control |

## Out of Scope

- Production deployment
- Blue/green or canary deployment strategies
- Automatic rollback (covered by 011-rollback-trigger)

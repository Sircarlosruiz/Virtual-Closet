---
id: 007-health-check-validation
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 007-Health Check Validation

## User Story

**As a** devops engineer  
**I want** health check validation after deployment  
**So that** failed deployments are caught immediately

## Acceptance Criteria

- [ ] **Given** a deployment completes, **When** the validation step runs, **Then** a post-deployment script checks `/health` endpoints
- [ ] **Given** pods are starting, **When** readiness is checked, **Then** the workflow waits for all pods to be in Ready state
- [ ] **Given** pods are not becoming ready, **When** the timeout is reached, **Then** the validation fails after 5 minutes
- [ ] **Given** health checks fail, **When** the failure is detected, **Then** the deployment is marked as failed
- [ ] **Given** deployment is marked failed, **When** the failure is confirmed, **Then** a rollback is triggered automatically or manually

## Technical Notes

- Use `kubectl get pods -l app=<name> -o jsonpath` to check pod readiness
- Use `curl -f` against `/health` endpoints with retry logic
- Implement retry loop with sleep intervals (e.g., 10s intervals, 30 max retries = 5 min)
- On failure, trigger rollback via `kubectl rollout undo` or notify for manual rollback
- Consider using Kubernetes Job for post-deployment validation

## Dependencies

### Requires
- 006-staging-workflow

### Enables
- 008-github-oidc

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Health endpoint returns 503 intermittently | Retry logic handles transient failures; only fails after sustained errors |
| Pod enters CrashLoopBackOff | Detected via pod status check; deployment marked as failed immediately |
| Health endpoint path changes | Validation fails; configuration should be centralized for easy updates |
| All pods are ready but health endpoint unreachable | Service/Ingress issue detected; validation fails with network error |

## Out of Scope

- Synthetic monitoring or ongoing health checks post-deployment
- Performance validation under load
- Database connectivity validation beyond basic health endpoint

---
id: 006-rollout-procedure
unit: 007-observability-recovery
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 007-observability-recovery
implemented: true
---

# Story: 006-Rollout Undo Procedure

## User Story

**As a** devops engineer  
**I want** the kubectl rollout undo procedure documented  
**So that** the team can rollback deployments quickly

## Acceptance Criteria

- [ ] **Given** the team needs to rollback a deployment, **When** they consult the documentation, **Then** a step-by-step rollback guide is available
- [ ] **Given** the rollback guide, **When** the engineer follows it, **Then** it includes commands for: `kubectl rollout undo`, `kubectl rollout status`, `kubectl rollout history`
- [ ] **Given** a rollback is executed, **When** the engineer verifies the result, **Then** verification steps are documented
- [ ] **Given** the rollback procedure, **When** the team estimates the time, **Then** the rollback time estimate is under 5 minutes
- [ ] **Given** the procedure is documented, **When** the team tests it, **Then** the rollback is tested and verified in a non-production environment

## Technical Notes

- Document the full rollback workflow: identify deployment, check history, undo to specific revision
- Include `kubectl rollout undo deployment/<name> --to-revision=<N>` for targeted rollbacks
- Verification: check pod status, health endpoints, and recent logs after rollback
- Store procedure in the project's runbook or ops documentation

## Dependencies

### Requires
- 005-node-alerting

### Enables
- 007-test-rollout

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| No rollout history available | Procedure documents how to redeploy the last known good image manually |
| Rollback fails due to image pull error | Procedure includes troubleshooting steps for image registry issues |
| Multiple replicas rolling back simultaneously | `kubectl rollout status` monitors progress until all replicas are updated |

## Out of Scope

- Automated rollback triggers (manual procedure only)
- Database migration rollbacks (covered in 008-restore-procedure)

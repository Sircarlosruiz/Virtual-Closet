---
id: 011-rollback-trigger
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: should
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 011-Rollback Trigger

## User Story

**As a** devops engineer  
**I want** a rollback trigger mechanism  
**So that** failed deployments can be rolled back quickly

## Acceptance Criteria

- [ ] **Given** a rollback is needed, **When** triggered manually, **Then** rollback is initiated via `workflow_dispatch`
- [ ] **Given** the rollback workflow runs, **When** the undo step executes, **Then** `kubectl rollout undo` is executed on the target deployment
- [ ] **Given** the rollout undo completes, **When** new pods start, **Then** the rollback waits for new pods to be Ready
- [ ] **Given** the rollback completes, **When** status is checked, **Then** rollback status is reported to the team
- [ ] **Given** the rollback starts, **When** it completes, **Then** the entire rollback completes within 5 minutes

## Technical Notes

- Create a separate `rollback.yml` workflow with `workflow_dispatch` trigger
- Accept inputs: environment (staging/production), deployment name
- Use `kubectl rollout undo deployment/<name> -n <namespace>`
- Wait with `kubectl rollout status deployment/<name> --timeout=300s`
- Send Slack notification on rollback success/failure (reuse notification pattern from 009)
- Consider adding input for specific revision: `kubectl rollout undo deployment/<name> --to-revision=N`

## Dependencies

### Requires
- 006-staging-workflow

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| No previous revision exists (first deployment) | Rollback fails with clear error: no revision to undo to |
| Rollback itself fails (image pull error on old revision) | Workflow fails; manual intervention required |
| Multiple rollbacks in quick succession | Each rollback operates on the current state; may need manual review |
| Rollback target revision has been pruned from history | Rollback fails; revision history limit should be configured |

## Out of Scope

- Automated rollback triggers (covered partially by 007-health-check-validation)
- Rollback of database migrations
- Point-in-time data recovery

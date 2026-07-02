---
id: 007-test-rollout
unit: 007-observability-recovery
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 007-observability-recovery
implemented: true
---

# Story: 007-Test Rollout Undo

## User Story

**As a** QA engineer  
**I want** to test the rollout undo procedure  
**So that** I can verify rollback works correctly

## Acceptance Criteria

- [ ] **Given** a test environment is ready, **When** a bad version is deployed, **Then** the deployment completes with the known-bad image
- [ ] **Given** the bad version is running, **When** `kubectl rollout undo` is executed, **Then** the rollback command completes successfully
- [ ] **Given** the rollback is executed, **When** pods are inspected, **Then** the previous version is restored successfully
- [ ] **Given** the previous version is restored, **When** health checks are run, **Then** service health is verified after rollback
- [ ] **Given** the rollback is complete, **When** the elapsed time is measured, **Then** the rollback completes within 5 minutes
- [ ] **Given** the test is complete, **When** the results are reviewed, **Then** test results are documented

## Technical Notes

- Deploy a deliberately broken image tag (e.g., `bad-image:test`) to test rollback
- Measure time from `kubectl rollout undo` to all pods reporting Ready
- Verify health endpoints return 200 after rollback
- Document the test in the QA test report template

## Dependencies

### Requires
- 006-rollout-procedure

### Enables
- 008-restore-procedure

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Rollback to a revision with deleted resources | `kubectl rollout undo` restores the replica set to the target revision's spec |
| Rollback during active traffic | Zero-downtime rollback; old pods serve traffic until new pods are Ready |
| Rollback fails midway | Procedure includes steps to retry or manually redeploy the last good image |

## Out of Scope

- Database rollback testing (covered in 009-test-restore)
- Production rollback testing (test in staging/non-production environment only)

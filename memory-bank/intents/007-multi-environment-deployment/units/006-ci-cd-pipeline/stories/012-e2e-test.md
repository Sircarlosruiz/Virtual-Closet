---
id: 012-e2e-test
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 012-E2E Test

## User Story

**As a** QA engineer  
**I want** to test the end-to-end CI/CD pipeline  
**So that** I can verify the entire flow works

## Acceptance Criteria

- [ ] **Given** a test PR is opened, **When** the workflow triggers, **Then** the PR workflow triggers and passes
- [ ] **Given** the PR workflow passes, **When** images are built, **Then** images build and push to registry successfully
- [ ] **Given** images are pushed, **When** deployment triggers, **Then** staging deployment succeeds
- [ ] **Given** deployment completes, **When** health checks run, **Then** health checks pass
- [ ] **Given** a rollback is triggered, **When** the rollback workflow runs, **Then** rollback works and restores previous state
- [ ] **Given** the full cycle runs, **When** timing is measured, **Then** the full cycle completes in under 15 minutes
- [ ] **Given** the test completes, **When** results are reviewed, **Then** results are documented with timing and status per stage

## Technical Notes

- Create a test plan document with step-by-step verification checklist
- Use a dedicated test branch and clean up resources after testing
- Measure and record timing for each stage: PR check, build, push, deploy, health check, rollback
- Verify OIDC authentication works end-to-end (no static credentials used)
- Test both success and failure paths (e.g., introduce a failing test, verify PR is blocked)
- Document any manual steps required during the E2E test

## Dependencies

### Requires
- 008-github-oidc

### Enables
- 013-workflow-docs

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Registry is slow during E2E test | Timing may exceed 15 min; document as infrastructure issue, not pipeline issue |
| Staging cluster is unavailable | E2E test fails at deployment stage; document cluster dependency |
| OIDC token exchange fails intermittently | Retry logic should handle; document if persistent |
| Rollback test leaves cluster in inconsistent state | Clean-up step should restore cluster to known good state |

## Out of Scope

- Load testing the pipeline under concurrent PRs
- Testing pipeline with production environment
- Chaos engineering / fault injection testing

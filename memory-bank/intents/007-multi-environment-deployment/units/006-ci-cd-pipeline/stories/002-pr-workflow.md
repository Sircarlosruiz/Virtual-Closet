---
id: 002-pr-workflow
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 002-PR Workflow

## User Story

**As a** devops engineer  
**I want** a GitHub Actions workflow triggered on PRs  
**So that** every PR is automatically built and tested

## Acceptance Criteria

- [ ] **Given** a pull request is opened or updated, **When** the event fires, **Then** the workflow triggers on `pull_request` events
- [ ] **Given** the workflow is running, **When** the frontend build step executes, **Then** the frontend builds successfully
- [ ] **Given** the workflow is running, **When** the backend build step executes, **Then** the backend builds successfully
- [ ] **Given** builds pass, **When** the test step executes, **Then** unit tests run for both frontend and backend
- [ ] **Given** all steps complete, **When** results are available, **Then** status is reported back to the PR
- [ ] **Given** any step fails, **When** the failure is detected, **Then** the PR is marked as failed

## Technical Notes

- Trigger on `pull_request` with types: `opened`, `synchronize`, `reopened`
- Use matrix strategy if frontend and backend can run in parallel
- Set `concurrency` to cancel redundant runs on the same PR
- Use `actions/checkout@v4` and appropriate language setup actions

## Dependencies

### Requires
- 001-workflow-structure

### Enables
- 003-docker-build

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| PR is updated rapidly (multiple pushes) | Previous runs are cancelled via concurrency group |
| PR targets a branch other than main | Workflow still triggers but may skip deploy steps |
| Build succeeds but tests fail | PR is marked as failed with clear test failure output |
| Workflow file itself has syntax errors | GitHub reports workflow validation error before execution |

## Out of Scope

- Docker image building (covered by 003-docker-build)
- Deployment to any environment
- Integration or E2E tests

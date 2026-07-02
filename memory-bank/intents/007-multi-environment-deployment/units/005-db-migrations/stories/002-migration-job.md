---
id: 002-migration-job
unit: 005-db-migrations
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 005-db-migrations
implemented: true
---

# Story: 002-Migration Job

## User Story

**As a** devops engineer  
**I want** a Kubernetes Job template for running Alembic migrations  
**So that** migrations execute automatically before deployment

## Acceptance Criteria

- [ ] **Given** the k8s manifests directory, **When** I inspect the Job template, **Then** a valid Kubernetes Job manifest for Alembic migrations is created
- [ ] **Given** the Job manifest, **When** I inspect the container spec, **Then** it uses the same backend image as the application
- [ ] **Given** the Job manifest, **When** I inspect the command, **Then** it runs `alembic upgrade head`
- [ ] **Given** the deployment pipeline, **When** a deployment is triggered, **Then** the Job runs as an init container or pre-deployment step
- [ ] **Given** a migration failure, **When** the Job executes, **Then** the Job fails and blocks the deployment
- [ ] **Given** the Job manifest, **When** I inspect the spec, **Then** a timeout is configured for the Job
- [ ] **Given** a running or completed Job, **When** I check logs, **Then** logs are accessible via `kubectl logs`

## Technical Notes

- Job should use the same image tag as the backend deployment to ensure migration code matches application code
- Consider using Helm templating for environment-specific configuration
- Job backoffLimit should be set to 0 to prevent retries on migration failures

## Dependencies

### Requires
- 001-review-alembic

### Enables
- 003-migration-validation

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Job times out | Job is marked as failed, deployment is blocked |
| Database is unreachable | Job fails with clear connection error message |
| Migration already applied | `alembic upgrade head` completes successfully with no-op |
| Concurrent Jobs | Only one Job should run at a time; use resource locks if needed |

## Out of Scope

- Database backup before migration
- Multi-database migration support
- Migration scheduling or cron-based execution

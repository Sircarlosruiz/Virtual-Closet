---
id: 007-celery-deployment
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 007-Celery Deployment

## User Story

**As a** devops engineer  
**I want** a Kubernetes Deployment for the Celery worker  
**So that** async tasks are processed

## Acceptance Criteria

- [ ] **Given** the manifest structure exists, **When** I create the Celery deployment, **Then** a Deployment with 1+ replicas is defined
- [ ] **Given** the deployment manifest, **When** I review the container image, **Then** it uses the same backend image
- [ ] **Given** the deployment manifest, **When** I review the command, **Then** the Celery worker command is configured
- [ ] **Given** the deployment manifest, **When** I review resource specs, **Then** resource requests and limits are defined
- [ ] **Given** the deployment manifest, **When** I review termination, **Then** graceful shutdown via SIGTERM handler is configured
- [ ] **Given** the deployment manifest, **When** I review environment, **Then** queue configuration is set via environment variables

## Technical Notes

- Celery worker command: celery -A app.celery_app worker --loglevel=info
- Graceful shutdown: terminationGracePeriodSeconds should be set to allow in-flight tasks to complete
- SIGTERM signal triggers Celery's warm shutdown (finish current task, then exit)

## Dependencies

### Requires
- 001-manifest-structure

### Enables
- 008-service-definitions

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Worker processing long task during rollout | SIGTERM triggers warm shutdown; task completes before pod terminates |
| RabbitMQ unavailable at startup | Worker retries connection; pod may fail liveness probe and restart |
| Queue name misconfigured | Worker connects but listens on wrong queue; tasks not processed |

## Out of Scope

- Celery beat scheduler configuration
- Celery task code implementation
- Celery flower monitoring UI

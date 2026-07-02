---
id: 012-liveness-probes
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 012-Liveness Probes

## User Story

**As a** devops engineer  
**I want** liveness probes for all services  
**So that** Kubernetes can restart hung containers

## Acceptance Criteria

- [ ] **Given** the frontend deployment, **When** I review the liveness probe, **Then** it uses HTTP GET /health with period 10s and timeout 5s
- [ ] **Given** the backend deployment, **When** I review the liveness probe, **Then** it uses HTTP GET /health with period 10s and timeout 5s
- [ ] **Given** the PostgreSQL StatefulSet, **When** I review the liveness probe, **Then** it uses tcpSocket on port 5432
- [ ] **Given** the MinIO StatefulSet, **When** I review the liveness probe, **Then** it uses HTTP GET /minio/health/live
- [ ] **Given** the RabbitMQ StatefulSet, **When** I review the liveness probe, **Then** it uses tcpSocket on port 5672
- [ ] **Given** the Celery deployment, **When** I review the liveness probe, **Then** it uses an exec probe or custom script

## Technical Notes

- Liveness probe failure triggers pod restart
- HTTP probes should return 200 OK for healthy containers
- tcpSocket probe checks if the port is open and accepting connections
- exec probe runs a command; exit code 0 = healthy, non-zero = unhealthy
- Celery liveness: celery inspect ping or custom script checking worker responsiveness

## Dependencies

### Requires
- 002-frontend-deployment
- 003-backend-deployment
- 004-postgresql-statefulset
- 005-minio-statefulset
- 006-rabbitmq-statefulset
- 007-celery-deployment

### Enables
- 016-manifest-validation

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Probe timeout too short | Pod restarts frequently under load; false positive failures |
| Health endpoint not implemented | Probe fails; pod enters CrashLoopBackOff |
| Probe period too long | Hung container not detected quickly; degraded service |

## Out of Scope

- Startup probes for slow-starting containers
- Custom health check endpoints implementation in application code
- Probe metrics and alerting

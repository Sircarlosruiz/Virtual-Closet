---
id: 013-readiness-probes
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 013-Readiness Probes

## User Story

**As a** devops engineer  
**I want** readiness probes for all services  
**So that** traffic is only routed to ready pods

## Acceptance Criteria

- [ ] **Given** the frontend deployment, **When** I review the readiness probe, **Then** it uses HTTP GET /health with initialDelay 10s
- [ ] **Given** the backend deployment, **When** I review the readiness probe, **Then** it uses HTTP GET /health (checks DB+MinIO connectivity) with initialDelay 15s
- [ ] **Given** the PostgreSQL StatefulSet, **When** I review the readiness probe, **Then** it uses exec pg_isready
- [ ] **Given** the MinIO StatefulSet, **When** I review the readiness probe, **Then** it uses HTTP GET /minio/health/ready
- [ ] **Given** the RabbitMQ StatefulSet, **When** I review the readiness probe, **Then** it uses HTTP GET /api/healthchecks
- [ ] **Given** the Celery deployment, **When** I review the readiness probe, **Then** it uses a custom readiness script

## Technical Notes

- Readiness probe failure removes pod from Service endpoints; no traffic routed
- Backend readiness should verify dependencies (DB, MinIO, RabbitMQ) are reachable
- initialDelaySeconds allows container time to initialize before first probe
- PostgreSQL pg_isready: exec command returns 0 when accepting connections
- Celery readiness: script checks if worker is registered and consuming from queue

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
| Backend readiness check fails due to DB down | Pod removed from endpoints; frontend receives 503 from backend |
| initialDelay too short | Probe fails during startup; pod never added to endpoints |
| Readiness probe too strict (checks all deps) | Transient dep failure removes pod; cascading failures |

## Out of Scope

- Startup probes for slow-starting containers
- Readiness gate for advanced traffic management
- Application-level dependency health endpoint implementation

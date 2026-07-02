---
id: 003-backend-deployment
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 003-Backend Deployment

## User Story

**As a** devops engineer  
**I want** a Kubernetes Deployment for the FastAPI backend  
**So that** the API runs with 2+ replicas

## Acceptance Criteria

- [ ] **Given** the manifest structure exists, **When** I create the backend deployment, **Then** the Deployment specifies 2 replicas
- [ ] **Given** the deployment manifest, **When** I review the container spec, **Then** the container image is pulled from a private registry
- [ ] **Given** the deployment manifest, **When** I review the update strategy, **Then** it uses a rolling update strategy
- [ ] **Given** the deployment manifest, **When** I review environment variables, **Then** they are sourced from a ConfigMap and/or Secret
- [ ] **Given** the deployment manifest, **When** I review resource specs, **Then** resource requests and limits are defined
- [ ] **Given** the deployment manifest, **When** I review probes, **Then** liveness and readiness probes are referenced

## Technical Notes

- FastAPI runs with uvicorn; worker count should match CPU limit
- Database connection pooling should be configured via environment variables
- Liveness and readiness probes should hit different endpoints if possible

## Dependencies

### Requires
- 001-manifest-structure

### Enables
- 008-service-definitions

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Database not reachable at startup | Readiness probe fails; pod not added to Service endpoints |
| Pod receives SIGTERM during request | Graceful shutdown period allows in-flight requests to complete |
| Image tag not found | Pod stays in ImagePullBackOff; old replicas continue serving traffic |

## Out of Scope

- Database migration execution (handled separately)
- Celery worker configuration (covered in 007)
- API code implementation

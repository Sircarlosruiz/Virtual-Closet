---
id: 005-backend-health
unit: 003-container-optimization
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 003-container-optimization
implemented: true
---

# Story: 005-Backend Health

## User Story

**As a** developer  
**I want** a /health endpoint in the FastAPI backend  
**So that** Kubernetes can verify the service is running

## Acceptance Criteria

- [ ] **Given** the backend service is running, **When** I send GET /health, **Then** it returns 200 OK
- [ ] **Given** the /health endpoint, **When** I inspect the response, **Then** it checks database connectivity
- [ ] **Given** the /health endpoint, **When** I inspect the response, **Then** it checks MinIO connectivity
- [ ] **Given** the /health endpoint, **When** I inspect the response body, **Then** it includes component statuses
- [ ] **Given** the /health endpoint, **When** I access it, **Then** it does not require authentication

## Technical Notes

- Use FastAPI router: @router.get("/health")
- Check PostgreSQL connection with simple query (SELECT 1)
- Check MinIO connection with bucket_exists or similar lightweight call
- Return JSON: { "status": "healthy", "components": { "database": "ok", "minio": "ok" } }
- Return 503 if any critical component is down

## Dependencies

### Requires
- 003-backend-docker

### Enables
- 006-health-check-instruction

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Database unreachable | Return 503 with component status showing database failure |
| MinIO unreachable | Return 503 with component status showing minio failure |
| Partial failure | Report which components are healthy/unhealthy |
| Endpoint accessed with POST | Return 405 Method Not Allowed |

## Out of Scope

- Detailed diagnostics or metrics
- Authentication or rate limiting
- Readiness vs liveness probe differentiation

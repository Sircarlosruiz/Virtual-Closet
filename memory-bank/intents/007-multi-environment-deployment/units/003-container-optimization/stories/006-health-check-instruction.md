---
id: 006-health-check-instruction
unit: 003-container-optimization
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 003-container-optimization
implemented: true
---

# Story: 006-Health Check Instruction

## User Story

**As a** developer  
**I want** HEALTHCHECK instructions in both Dockerfiles  
**So that** Docker can monitor container health outside Kubernetes

## Acceptance Criteria

- [ ] **Given** the frontend Dockerfile, **When** I review it, **Then** it has a HEALTHCHECK instruction using the /health endpoint
- [ ] **Given** the backend Dockerfile, **When** I review it, **Then** it has a HEALTHCHECK instruction using the /health endpoint
- [ ] **Given** the HEALTHCHECK instruction, **When** I review the parameters, **Then** interval is 30s, timeout is 5s, retries is 3
- [ ] **Given** the built images, **When** I run docker run and inspect, **Then** HEALTHCHECK passes in local docker run test

## Technical Notes

- Frontend: HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:3000/health || exit 1
- Backend: HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
- Install curl in images (or use wget as alternative)
- Consider using CMD-SHELL for more complex health checks

## Dependencies

### Requires
- 004-frontend-health
- 005-backend-health

### Enables
- 010-test-images

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| curl not installed in image | Install curl or use wget as alternative |
| Health check fails during startup | Use start-period parameter to allow startup time |
| Container port differs from default | Use correct port in HEALTHCHECK command |

## Out of Scope

- Kubernetes probe configuration (covered in deployment unit)
- Custom health check scripts
- Integration with monitoring systems

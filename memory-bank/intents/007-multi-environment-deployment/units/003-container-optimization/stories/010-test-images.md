---
id: 010-test-images
unit: 003-container-optimization
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 003-container-optimization
implemented: true
---

# Story: 010-Test Images

## User Story

**As a** developer  
**I want** to test the built images locally  
**So that** I can verify they work before pushing to registry

## Acceptance Criteria

- [ ] **Given** the frontend Dockerfile, **When** I run docker build, **Then** the frontend image builds successfully
- [ ] **Given** the backend Dockerfile, **When** I run docker build, **Then** the backend image builds successfully
- [ ] **Given** the built images, **When** I check their sizes, **Then** image sizes are within targets (frontend < 200MB, backend < 150MB)
- [ ] **Given** the frontend container, **When** I access it, **Then** the frontend serves pages correctly in container
- [ ] **Given** the backend container, **When** I send API requests, **Then** the backend responds to API requests in container
- [ ] **Given** the running containers, **When** I execute whoami, **Then** non-root user is confirmed (whoami in container)

## Technical Notes

- Use docker run -p to map ports and test locally
- Test frontend: curl http://localhost:3000
- Test backend: curl http://localhost:8000/api/health
- Verify non-root: docker exec <container> whoami
- Check image size: docker images <image-name>
- Test with minimal environment variables to ensure defaults work

## Dependencies

### Requires
- 008-optimize-layers

### Enables
- 011-security-scan

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Container exits immediately | Check logs with docker logs, verify CMD/ENTRYPOINT |
| Port already in use | Use different host port or stop conflicting service |
| Environment variables missing | Ensure defaults are set or document required vars |

## Out of Scope

- Integration testing with database
- Load testing
- Multi-container testing with docker-compose

---
id: 006-test-dev-startup
unit: 001-dev-environment
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 006-Test Full Development Environment Startup

## User Story

**As a** team lead  
**I want** to verify that the entire dev environment starts successfully with a single command  
**So that** all developers can get productive quickly without debugging Docker issues

## Acceptance Criteria

- [ ] **Given** a developer runs `docker-compose up` from project root, **When** startup completes, **Then** all containers are running and healthy
- [ ] **Given** services start, **When** checking logs, **Then** no critical errors are present
- [ ] **Given** frontend is ready, **When** navigating to `http://localhost:3000`, **Then** app loads successfully
- [ ] **Given** backend is ready, **When** calling `http://localhost:8000/health`, **Then** health check returns 200 OK
- [ ] **Given** database is initialized, **When** connecting via psql, **Then** migrations have been applied
- [ ] **Given** RabbitMQ is running, **When** checking management console at `http://localhost:15672`, **Then** it responds with login page
- [ ] **Given** MinIO is running, **When** accessing `http://localhost:9001`, **Then** console loads and can authenticate

## Technical Notes

- Test on a clean machine (as if fresh clone)
- Document startup time (should be < 5 minutes)
- List all service endpoints and default credentials

## Dependencies

### Requires
- 001-refactor-docker-compose
- 002-configure-alembic-auto
- 003-hot-reload-frontend
- 004-hot-reload-backend
- 005-env-example

### Enables
- 007-dev-guide

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Docker daemon not running | Clear error message |
| Port already in use | Error shows which service conflicts |
| Out of disk space | Docker provides clear error |
| Network connectivity issues | Error during image pull or service startup |

## Out of Scope

- Troubleshooting individual service issues
- GPU setup (optional, separate documentation)

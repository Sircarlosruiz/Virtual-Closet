---
id: 003-backend-docker
unit: 003-container-optimization
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 003-container-optimization
implemented: true
---

# Story: 003-Backend Docker

## User Story

**As a** developer  
**I want** a multi-stage Dockerfile for the FastAPI backend  
**So that** the production image is small and optimized

## Acceptance Criteria

- [ ] **Given** the backend service, **When** I build the Docker image, **Then** a multi-stage build is used: deps → runtime
- [ ] **Given** the Dockerfile, **When** I review the base image, **Then** it uses python:3.11-slim
- [ ] **Given** the final stage, **When** I inspect installed packages, **Then** only production dependencies are installed (no dev/test packages)
- [ ] **Given** the built image, **When** I check its size, **Then** it is less than 150MB
- [ ] **Given** the Dockerfile, **When** I run docker build, **Then** the build succeeds without errors

## Technical Notes

- Use pip install --no-cache-dir to reduce image size
- Separate requirements files: requirements.txt (prod) and requirements-dev.txt (dev)
- Install system dependencies in builder stage, copy only needed binaries
- Use virtual environment in final stage for clean dependency isolation

## Dependencies

### Requires
- 001-analyze-dockerfile

### Enables
- 006-health-check-instruction

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Python package build fails | Clear error message indicating missing system dependency |
| C extension compilation fails | Document required build tools in builder stage |
| Virtual environment path issues | Use consistent venv path across stages |

## Out of Scope

- Development Dockerfile with debug tools
- Database migration scripts
- Celery worker containers

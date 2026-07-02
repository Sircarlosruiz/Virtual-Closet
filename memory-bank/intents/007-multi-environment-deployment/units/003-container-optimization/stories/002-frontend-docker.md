---
id: 002-frontend-docker
unit: 003-container-optimization
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 003-container-optimization
implemented: true
---

# Story: 002-Frontend Docker

## User Story

**As a** developer  
**I want** a multi-stage Dockerfile for the Next.js 14 frontend  
**So that** the production image is small and optimized

## Acceptance Criteria

- [ ] **Given** the frontend service, **When** I build the Docker image, **Then** a multi-stage build is used: deps → build → runner
- [ ] **Given** the Dockerfile, **When** I review the base image, **Then** it uses node:20-alpine
- [ ] **Given** the final stage, **When** I inspect the image contents, **Then** only production artifacts are present (no source code, no dev dependencies)
- [ ] **Given** the built image, **When** I check its size, **Then** it is less than 200MB
- [ ] **Given** the Dockerfile, **When** I run docker build, **Then** the build succeeds without errors

## Technical Notes

- Next.js 14 requires standalone output mode for optimal Docker builds
- Set `output: 'standalone'` in next.config.js
- Copy only the standalone output and static/assets directories to final stage
- Use npm ci for deterministic dependency installation

## Dependencies

### Requires
- 001-analyze-dockerfile

### Enables
- 006-health-check-instruction

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Next.js build fails | Build fails with clear error message, no partial image |
| Static assets missing | Verify public/ and .next/static/ are copied correctly |
| node_modules platform mismatch | Use npm ci with target platform architecture |

## Out of Scope

- Development Dockerfile with hot reload
- Docker Compose configuration
- CI/CD integration

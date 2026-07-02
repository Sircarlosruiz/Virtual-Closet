---
id: 003-docker-build
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 003-Docker Build

## User Story

**As a** devops engineer  
**I want** GitHub Actions to build Docker images  
**So that** images are built consistently

## Acceptance Criteria

- [ ] **Given** the CI pipeline runs, **When** Docker buildx is configured, **Then** buildx is set up with multi-platform support
- [ ] **Given** the frontend code has changed, **When** the build step runs, **Then** the frontend Docker image builds successfully
- [ ] **Given** the backend code has changed, **When** the build step runs, **Then** the backend Docker image builds successfully
- [ ] **Given** repeated builds occur, **When** layer caching is enabled, **Then** build cache is used to speed up subsequent builds
- [ ] **Given** the build starts, **When** it completes, **Then** the entire build finishes within 10 minutes

## Technical Notes

- Use `docker/setup-buildx-action` for buildx configuration
- Use `docker/build-push-action` with `cache-from` and `cache-to` for layer caching
- Use GitHub Actions cache backend (`type=gha`) for efficient caching
- Build images without pushing at this stage (push covered in 005-push-registry)
- Multi-stage Dockerfiles should be used for optimized image sizes

## Dependencies

### Requires
- 002-pr-workflow

### Enables
- 004-unit-tests

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Dockerfile has syntax errors | Build fails with clear Docker error message |
| Build cache is corrupted | Build falls back to full build without cache |
| Base image is unavailable | Build fails with pull error; retry logic should handle transient failures |
| Build exceeds 10-minute timeout | Job is cancelled and marked as failed |

## Out of Scope

- Pushing images to registry (covered by 005-push-registry)
- Image vulnerability scanning
- Multi-architecture builds beyond amd64

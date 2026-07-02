---
id: 005-push-registry
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 005-Push Registry

## User Story

**As a** devops engineer  
**I want** CI to push images to a private registry  
**So that** Kubernetes can pull them for deployment

## Acceptance Criteria

- [ ] **Given** images are built, **When** tagging occurs, **Then** images are tagged with commit SHA and branch name
- [ ] **Given** images are tagged, **When** the push step runs, **Then** images are pushed to private registry (Docker Hub/GHCR)
- [ ] **Given** the push is triggered, **When** the branch is not main or a release tag, **Then** push is skipped
- [ ] **Given** push occurs, **When** credentials are needed, **Then** registry credentials are read from GitHub Secrets
- [ ] **Given** push completes, **When** verification runs, **Then** the image is confirmed pullable from the registry

## Technical Notes

- Use `docker/login-action` for registry authentication
- GHCR preferred: `ghcr.io/${{ github.repository }}`
- Tag strategy: `sha-<short-sha>`, `<branch-name>-latest`, `latest` (on main only)
- Use `docker/build-push-action` with `push: true` conditionally based on branch
- Store `REGISTRY_USERNAME` and `REGISTRY_TOKEN` as GitHub Secrets

## Dependencies

### Requires
- 004-unit-tests

### Enables
- 006-staging-workflow

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Registry is temporarily unavailable | Push retries with exponential backoff; fails after max retries |
| Image tag already exists | Image is overwritten (or skipped based on policy) |
| GitHub Secrets are misconfigured | Push fails with authentication error; clear log message |
| Push succeeds but pull verification fails | Step fails with image digest mismatch or pull error |

## Out of Scope

- Image vulnerability scanning
- Image signing (cosign/Notary)
- Multi-region registry replication

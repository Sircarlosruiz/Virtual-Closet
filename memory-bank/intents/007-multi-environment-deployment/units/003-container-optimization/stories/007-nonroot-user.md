---
id: 007-nonroot-user
unit: 003-container-optimization
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 003-container-optimization
implemented: true
---

# Story: 007-Nonroot User

## User Story

**As a** devops engineer  
**I want** containers to run as non-root users  
**So that** the attack surface is minimized

## Acceptance Criteria

- [ ] **Given** the frontend Dockerfile, **When** I review it, **Then** it creates and switches to a non-root user
- [ ] **Given** the backend Dockerfile, **When** I review it, **Then** it creates and switches to a non-root user
- [ ] **Given** the non-root user, **When** I inspect permissions, **Then** the user has minimal permissions needed
- [ ] **Given** the built images, **When** I run the container, **Then** the container starts successfully as non-root
- [ ] **Given** the running container, **When** I check logs, **Then** there are no permission errors

## Technical Notes

- Frontend: Create node user with home directory, chown .next and public folders
- Backend: Create appuser with home directory, chown application directory
- Use USER instruction after all root-required operations
- Ensure application files are owned by the non-root user
- Use numeric UID/GID for better portability (e.g., UID 1001)

## Dependencies

### Requires
- 006-health-check-instruction

### Enables
- 010-test-images

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Application needs to write to directory | Ensure directory is owned by non-root user or writable |
| Port binding below 1024 | Use non-privileged port (3000 for frontend, 8000 for backend) |
| Health check fails due to permissions | Ensure curl/wget can access localhost without root |

## Out of Scope

- Pod Security Policies in Kubernetes
- Seccomp profiles
- AppArmor configuration

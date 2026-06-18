---
id: 007-dev-guide
unit: 001-dev-environment
intent: 007-multi-environment-deployment
status: complete
priority: should
created: 2026-06-17T14:45:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 007-Document Local Development Quick-Start Guide

## User Story

**As a** new developer joining the project  
**I want** clear documentation on how to set up and use the local development environment  
**So that** I can start contributing productively in under 30 minutes

## Acceptance Criteria

- [ ] **Given** a new developer reads the guide, **When** they follow steps, **Then** they have a working dev environment
- [ ] **Given** the guide exists, **When** checking root README or DEVELOPMENT.md, **Then** it covers: prerequisites, setup, running services, accessing endpoints
- [ ] **Given** hot-reload enabled, **When** documented, **Then** developer understands how to edit code and see changes
- [ ] **Given** migrations auto-run, **When** documented, **Then** developer knows how to add new migrations
- [ ] **Given** common issues arise, **When** consulting the guide, **Then** troubleshooting section addresses them

## Technical Notes

- Include Docker installation instructions (link to Docker docs)
- Document all service URLs and default credentials
- Add optional GPU setup instructions (if available)
- Include commands for running tests locally

## Dependencies

### Requires
- 001-refactor-docker-compose
- 002-configure-alembic-auto
- 003-hot-reload-frontend
- 004-hot-reload-backend
- 005-env-example
- 006-test-dev-startup

### Enables
- None (concludes dev environment setup)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Developer uses Windows (WSL2) | Specific WSL2 instructions included |
| Developer uses Mac with Apple Silicon | Potential ARM-specific instructions included |
| Developer has existing containers/volumes | Guide recommends cleaning up before fresh start |

## Out of Scope

- Production deployment procedures (Unit 2)
- Kubernetes setup (Unit 4)

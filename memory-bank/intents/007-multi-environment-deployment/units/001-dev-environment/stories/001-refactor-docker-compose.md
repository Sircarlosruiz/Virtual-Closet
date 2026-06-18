---
id: 001-refactor-docker-compose
unit: 001-dev-environment
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 001-Refactor docker-compose.yml

## User Story

**As a** developer  
**I want** to refactor docker-compose.yml to remove obsolete services (catvton) and clean up unused volumes  
**So that** the development environment is cleaner and maintenance is easier

## Acceptance Criteria

- [ ] **Given** docker-compose.yml contains catvton service, **When** refactoring, **Then** catvton service is removed
- [ ] **Given** catvton_cache volume is unused, **When** refactoring, **Then** catvton_cache volume is removed
- [ ] **Given** existing services need to continue working, **When** refactoring, **Then** all other services (postgres, minio, rabbitmq, frontend, backend, celery) remain intact
- [ ] **Given** docker-compose.yml is refactored, **When** running `docker-compose up`, **Then** all remaining services start successfully

## Technical Notes

- Verify catvton service is not referenced anywhere in backend code before removal
- Update docker-compose version if needed (target: v3.8+)
- Validate YAML syntax after refactoring

## Dependencies

### Requires
- None

### Enables
- 002-configure-alembic-auto-migration
- 003-add-hot-reload-frontend
- 004-add-hot-reload-backend

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Other parts of codebase reference catvton | Search and fix references before removal |
| catvton_cache volume has mounted data | Document backup/migration if needed |
| Networks or service links to catvton exist | Update dependencies after removal |

## Out of Scope

- Adding new services to compose
- Migrating to production k8s configurations (Unit 4)

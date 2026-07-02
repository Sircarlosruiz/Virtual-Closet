---
id: 002-configure-alembic-auto
unit: 001-dev-environment
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 001-dev-environment-setup
implemented: true
---

# Story: 002-Configure Alembic Auto-Migration on Startup

## User Story

**As a** developer  
**I want** database migrations to automatically run when `docker-compose up` starts PostgreSQL  
**So that** my local development database schema is always up-to-date without manual intervention

## Acceptance Criteria

- [ ] **Given** docker-compose starts, **When** PostgreSQL container initializes, **Then** Alembic migrations run automatically
- [ ] **Given** migrations complete successfully, **When** checking the database, **Then** all schema changes are applied
- [ ] **Given** new migrations are added to `backend/alembic/versions/`, **When** restarting containers, **Then** new migrations run automatically
- [ ] **Given** migrations fail, **When** checking container logs, **Then** error messages clearly identify the failure

## Technical Notes

- Use PostgreSQL initialization script (entrypoint or volume mount) to run `alembic upgrade head`
- Ensure Alembic config in backend is properly set up
- Document Alembic best practices in local development guide

## Dependencies

### Requires
- 001-refactor-docker-compose (catvton removed)

### Enables
- 005-create-env-example

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Migration file is malformed | Container logs show error; migration stops |
| Database already migrated | `alembic upgrade head` is idempotent; no error |
| New migration added during development | Auto-runs on next `docker-compose up` |

## Out of Scope

- Creating new Alembic migrations (handled by backend development)
- Testing migrations in k8s (Unit 5)

---
id: 004-hot-reload-backend
unit: 001-dev-environment
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 001-dev-environment-setup
implemented: true
---

# Story: 004-Enable Hot-Reload for Backend Development

## User Story

**As a** backend developer  
**I want** my FastAPI code changes to automatically reload the server without container restart  
**So that** I can test API changes quickly without losing workflow

## Acceptance Criteria

- [ ] **Given** backend container is running with `docker-compose`, **When** I modify `.py` files, **Then** FastAPI reloads automatically within 1-2 seconds
- [ ] **Given** I add a new endpoint, **When** I save the file, **Then** endpoint is immediately available without restart
- [ ] **Given** I make a syntax error, **When** I save, **Then** error is logged and next request shows error details
- [ ] **Given** dependencies are updated via `uv add`, **When** I restart the container, **Then** new dependencies are available

## Technical Notes

- FastAPI dev server supports `--reload` flag with `uvicorn`
- Use `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- Ensure volume mount for `/backend` directory in docker-compose
- Python dependencies managed via uv (UV lock file)

## Dependencies

### Requires
- 001-refactor-docker-compose

### Enables
- 006-document-env-example

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| .env file changed | Container restart required |
| Database schema changes | Alembic migration auto-runs |
| Multiple .py files changed at once | All reload correctly |
| Import errors in changed file | Error logged, server continues running |

## Out of Scope

- Frontend API hot-reload
- Production FastAPI optimization

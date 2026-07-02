---
id: 005-env-example
unit: 001-dev-environment
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 001-dev-environment-setup
implemented: true
---

# Story: 005-Create and Document .env.example Template

## User Story

**As a** developer onboarding to the project  
**I want** a `.env.example` file showing all required environment variables  
**So that** I can quickly set up my local development environment without guessing

## Acceptance Criteria

- [ ] **Given** a new developer clones the repo, **When** they look at `.env.example`, **Then** they see all required env vars with comments
- [ ] **Given** .env.example is committed to git, **When** someone runs `cp .env.example .env`, **Then** they have a working dev setup
- [ ] **Given** the `.env` file is used in docker-compose, **When** values are read, **Then** services connect correctly
- [ ] **Given** sensitive defaults, **When** documenting in .env.example, **Then** placeholder values (e.g., `POSTGRES_PASSWORD=dev_password`) are clearly marked as insecure

## Technical Notes

- .env.example is gitignored, so create and commit the example file
- Include comments explaining each variable
- Example values should be safe for local development
- Document which vars are required vs optional

## Dependencies

### Requires
- 001-refactor-docker-compose
- 002-configure-alembic-auto
- 003-hot-reload-frontend
- 004-hot-reload-backend

### Enables
- 006-test-full-dev-startup
- 007-dev-guide

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User has existing .env file | Example doesn't overwrite it |
| New env var added during development | Documented in .env.example with comment |
| Secret values | Example has safe placeholder values |

## Out of Scope

- Managing secrets for CI/CD (Unit 6)
- Production .env configuration

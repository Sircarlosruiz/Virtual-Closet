---
id: 004-migration-dryrun
unit: 005-db-migrations
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 005-db-migrations
implemented: true
---

# Story: 004-Migration Dry-Run

## User Story

**As a** backend developer  
**I want** a migration dry-run mechanism  
**So that** I can preview what migrations will do before executing them

## Acceptance Criteria

- [ ] **Given** pending migrations, **When** I run `alembic upgrade --sql`, **Then** SQL is generated without executing against the database
- [ ] **Given** dry-run output, **When** I review it, **Then** the generated SQL is correct and matches expected schema changes
- [ ] **Given** the CI/CD pipeline, **When** a migration PR is opened, **Then** dry-run output is included in the pipeline logs
- [ ] **Given** a dry-run execution, **When** it completes, **Then** the results are logged for audit purposes

## Technical Notes

- `alembic upgrade head --sql` outputs SQL without executing
- Consider capturing dry-run output as a CI artifact for PR review
- Dry-run should run against a schema that matches the target environment

## Dependencies

### Requires
- 003-migration-validation

### Enables
- 005-rollback-procedure

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Dry-run produces invalid SQL | Flag the migration as problematic before deployment |
| No pending migrations | Dry-run outputs "no migrations to apply" or equivalent |
| Large migration with many changes | Dry-run output is still readable and reviewable |
| Dry-run environment differs from target | Document the limitation and ensure schema parity |

## Out of Scope

- Automatic SQL review or linting
- Applying dry-run changes to a test database
- Performance analysis of migration SQL

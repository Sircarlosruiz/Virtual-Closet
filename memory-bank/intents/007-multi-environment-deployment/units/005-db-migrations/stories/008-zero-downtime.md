---
id: 008-zero-downtime
unit: 005-db-migrations
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 005-db-migrations
implemented: true
---

# Story: 008-Zero-Downtime

## User Story

**As a** backend developer  
**I want** to validate that migrations can run with zero downtime  
**So that** deployments don't interrupt users

## Acceptance Criteria

- [ ] **Given** a migration, **When** I review it, **Then** only additive changes are used (new nullable columns, new tables, new indexes)
- [ ] **Given** a migration that renames or drops a column, **When** I review it, **Then** a multi-step process is documented (add new → migrate data → switch → drop old)
- [ ] **Given** a migration, **When** I verify backward compatibility, **Then** the old application code works with the new schema
- [ ] **Given** a running migration, **When** pods are serving traffic, **Then** they continue serving requests without interruption
- [ ] **Given** a migration in progress, **When** concurrent traffic is sent, **Then** the application handles it correctly under load

## Technical Notes

- Additive-only rule: new columns must be nullable or have defaults
- Column renames require a multi-step approach across multiple deployments
- Consider using expand-contract pattern for complex schema changes
- Test with `pg_stat_activity` to check for lock contention during migration

## Dependencies

### Requires
- 007-test-failure

### Enables
- 009-migration-guide

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Migration requires exclusive table lock | Migration waits for lock; document expected wait time |
| Old code writes to dropped column | Multi-step process prevents this; old code writes to both columns |
| Large table migration causes lock timeout | Use `LOCK_TIMEOUT` and retry logic; consider `CONCURRENTLY` for indexes |
| Application reads cache during migration | Cache invalidation strategy accounts for schema changes |

## Out of Scope

- Blue-green deployment strategy for database changes
- Database replication or read replica management
- Schema versioning in application code

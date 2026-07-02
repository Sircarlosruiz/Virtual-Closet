---
id: 009-test-backup
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 009-Test Backup

## User Story

**As a** devops engineer  
**I want** to verify that backups are created and stored correctly  
**So that** I can trust the backup system

## Acceptance Criteria

- [ ] **Given** the CronJob, **When** manually triggering it, **Then** a backup is created successfully
- [ ] **Given** the backup is created, **When** inspecting Hetzner Object Storage, **Then** the backup file appears in the bucket
- [ ] **Given** the backup file, **When** downloading and inspecting it, **Then** it is a valid gzip file
- [ ] **Given** the backup file, **When** decompressing and inspecting contents, **Then** it contains expected database tables
- [ ] **Given** the backup file, **When** checking its size, **Then** the size is reasonable for the database content

## Technical Notes

- Manual trigger via `kubectl create job --from=cronjob/backup-job backup-test`
- Verify gzip with `gunzip -t` command
- Validate SQL dump by checking for expected table names
- Compare backup size with database size for reasonableness

## Dependencies

### Requires
- 008-backup-cronjob

### Enables
- 010-test-restore

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Backup is empty | Test fails, investigate CronJob execution |
| Backup corrupted | gunzip test fails, alert triggered |
| Backup too small | Investigate pg_dump execution |

## Out of Scope

- Automated backup validation on schedule
- Backup integrity checksums

---
id: 008-backup-cronjob
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 008-Backup CronJob

## User Story

**As a** devops engineer  
**I want** an automated PostgreSQL backup cronjob  
**So that** database backups are created daily without manual intervention

## Acceptance Criteria

- [ ] **Given** the cluster, **When** inspecting CronJobs, **Then** a CronJob exists that runs daily at 02:00 UTC
- [ ] **Given** the CronJob executes, **When** inspecting the job logs, **Then** it runs `pg_dump` and compresses the output
- [ ] **Given** the backup is created, **When** inspecting Hetzner Object Storage, **Then** the backup is uploaded to the configured bucket
- [ ] **Given** the backup file, **When** inspecting the filename, **Then** it includes a timestamp (e.g., `backup-2026-06-17.sql.gz`)
- [ ] **Given** the CronJob configuration, **When** inspecting the ConfigMap, **Then** the schedule is configurable via ConfigMap

## Technical Notes

- Use Kubernetes `CronJob` resource with `schedule: "0 2 * * *"`
- Backup script should use `pg_dump` with `gzip` compression
- Upload via `aws s3 cp` or equivalent S3-compatible client
- ConfigMap should contain schedule, bucket name, and retention policy
- ServiceAccount with S3 credentials should be used

## Dependencies

### Requires
- 007-persistent-volumes

### Enables
- 009-test-backup

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Backup fails | Job marked as failed, alert triggered |
| S3 upload fails | Retry logic or manual intervention required |
| Database locked | pg_dump waits or uses `--no-lock` option |

## Out of Scope

- Incremental backups
- Backup encryption (covered by security stories)

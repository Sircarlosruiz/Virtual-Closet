---
id: 012-terraform-state
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: should
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 012-Terraform State

## User Story

**As a** devops engineer  
**I want** Terraform state stored in a remote backend  
**So that** state is shared and locked across team members

## Acceptance Criteria

- [ ] **Given** the Terraform configuration, **When** inspecting `backend.tf`, **Then** a remote backend is configured (S3-compatible or Hetzner Object Storage)
- [ ] **Given** the remote backend, **When** multiple team members run `terraform plan`, **Then** state locking prevents concurrent modifications
- [ ] **Given** the state file, **When** inspecting backend configuration, **Then** the state file is encrypted at rest
- [ ] **Given** the backend configuration, **When** inspecting `backend.tf`, **Then** the configuration is documented with comments
- [ ] **Given** the team, **When** running `terraform plan` and `terraform apply`, **Then** operations complete without state conflicts

## Technical Notes

- Use S3-compatible backend with Hetzner Object Storage or AWS S3
- Enable state locking via DynamoDB or equivalent
- Use server-side encryption (SSE) for state file at rest
- Backend configuration should not contain credentials (use environment variables or IAM roles)
- State file should be versioned for recovery

## Dependencies

### Requires
- 003-hcloud-vpc

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| State lock stuck | Manual lock release procedure documented |
| Backend unreachable | Terraform fails with clear error, no state modification |
| State file corrupted | Restore from versioned backup |

## Out of Scope

- State file migration from local to remote
- Multi-workspace state management

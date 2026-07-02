---
id: 010-branch-protection
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: should
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 010-Branch Protection

## User Story

**As a** devops engineer  
**I want** branch protection rules on main  
**So that** code quality gates are enforced

## Acceptance Criteria

- [ ] **Given** a PR targets main, **When** merge is attempted, **Then** a PR is required before merge
- [ ] **Given** a PR is open, **When** status checks are evaluated, **Then** CI workflow status checks must pass
- [ ] **Given** a PR is ready for review, **When** merge is attempted, **Then** at least 1 review is required
- [ ] **Given** the main branch is protected, **When** a force push is attempted, **Then** the force push is rejected
- [ ] **Given** the main branch is protected, **When** a direct push is attempted, **Then** the direct push is rejected
- [ ] **Given** a PR is approved, **When** main has new commits, **Then** the branch must be up to date before merge

## Technical Notes

- Configure via GitHub UI or `gh api` / Terraform GitHub provider
- Required status checks: `ci` workflow (build, test jobs)
- Enable "Require branches to be up to date before merging"
- Enable "Do not allow force pushes" and "Do not allow deletions"
- Consider enabling "Require linear history" for clean commit history
- Use GitHub API or CLI to automate rule configuration for reproducibility

## Dependencies

### Requires
- 002-pr-workflow

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Admin needs to bypass protection for hotfix | Admin bypass is allowed but logged for audit |
| CI check is stale (not re-run after rebase) | Merge is blocked until CI re-runs and passes |
| Required reviewer is the PR author | Review from author is not counted; another reviewer required |
| Status check name changes in workflow | Branch protection must be updated to match new check name |

## Out of Scope

- Branch protection for release branches
- Merge queue configuration
- Automated dependency update exceptions (e.g., Dependabot auto-merge)

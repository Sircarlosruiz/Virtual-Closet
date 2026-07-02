---
id: 009-notifications
unit: 006-ci-cd-pipeline
intent: 007-multi-environment-deployment
status: complete
priority: should
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 006-ci-cd-pipeline
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 009-Notifications

## User Story

**As a** devops engineer  
**I want** deployment notifications  
**So that** the team knows when deployments succeed or fail

## Acceptance Criteria

- [ ] **Given** a deployment succeeds, **When** the success is confirmed, **Then** a Slack notification is sent for deployment success
- [ ] **Given** a deployment fails, **When** the failure is detected, **Then** a Slack notification is sent for deployment failure
- [ ] **Given** a notification is sent, **When** the content is reviewed, **Then** it includes commit SHA, deployer, environment, and status
- [ ] **Given** the webhook URL is needed, **When** the notification step runs, **Then** the notification webhook is read from GitHub Secrets
- [ ] **Given** the notification service is down, **When** the notification fails, **Then** the pipeline continues without blocking

## Technical Notes

- Use `slackapi/slack-github-action` or `curl` to post to Slack webhook
- Notification should be in a final step with `if: always()` to run regardless of prior step outcomes
- Include: commit SHA (`github.sha`), actor (`github.actor`), environment name, workflow status
- Store `SLACK_WEBHOOK_URL` as a GitHub Secret
- Use `continue-on-error: true` so notification failures don't fail the pipeline

## Dependencies

### Requires
- 006-staging-workflow

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Slack webhook URL is invalid | Notification fails silently; pipeline continues |
| Slack is down | Notification times out; pipeline continues due to `continue-on-error` |
| Deployment is triggered by automated merge | Deployer field shows the merge actor or "automated" |
| Multiple deployments in quick succession | Each deployment sends its own notification with unique commit SHA |

## Out of Scope

- Email notifications
- PagerDuty or Opsgenie integration
- Notification routing based on failure type

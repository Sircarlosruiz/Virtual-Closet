---
id: 004-pod-alerting
unit: 007-observability-recovery
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 007-observability-recovery
implemented: true
---

# Story: 004-Pod Crash Alerting

## User Story

**As a** devops engineer  
**I want** alerting when pods crash  
**So that** the team is notified of service failures

## Acceptance Criteria

- [ ] **Given** a pod enters CrashLoopBackOff state, **When** the state is detected, **Then** an alert is triggered
- [ ] **Given** a pod restarts more than 3 times in 5 minutes, **When** the threshold is exceeded, **Then** an alert is triggered
- [ ] **Given** an alert is triggered, **When** the alert payload is assembled, **Then** it includes: pod name, namespace, restart count, last log lines
- [ ] **Given** an alert fires, **When** the notification is sent, **Then** it is delivered to Slack or email
- [ ] **Given** the alert configuration, **When** a team member reviews it, **Then** the alert threshold is configurable via config file or environment variable

## Technical Notes

- Use Prometheus + Alertmanager or Kubernetes-native alerting (e.g., kube-state-metrics)
- Alert rule for CrashLoopBackOff: `kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"}`
- Alert rule for restart frequency: `increase(kube_pod_container_status_restarts_total[5m]) > 3`
- Include last N log lines from the crashed container in the alert payload
- Slack webhook or SMTP integration for notification delivery

## Dependencies

### Requires
- 002-structured-logging-fe
- 003-structured-logging-be

### Enables
- 005-node-alerting

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Alert notification channel is down | Alerts are queued and retried; fallback to secondary channel if configured |
| Pod is intentionally restarted (deployment rollout) | Alert is suppressed during active rollouts via maintenance window |
| Multiple pods crash simultaneously | Each pod generates a separate alert; alerts are not deduplicated unless identical |

## Out of Scope

- Node-level alerting (covered in 005-node-alerting)
- Auto-remediation or self-healing (manual intervention required)

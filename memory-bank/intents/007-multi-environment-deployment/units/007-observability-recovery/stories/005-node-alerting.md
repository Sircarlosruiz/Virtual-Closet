---
id: 005-node-alerting
unit: 007-observability-recovery
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 007-observability-recovery
implemented: true
---

# Story: 005-Node Failure Alerting

## User Story

**As a** devops engineer  
**I want** alerting when nodes go offline  
**So that** infrastructure issues are detected quickly

## Acceptance Criteria

- [ ] **Given** a node becomes NotReady, **When** the condition is detected, **Then** an alert is triggered
- [ ] **Given** a node's disk usage exceeds 85%, **When** the threshold is crossed, **Then** an alert is triggered
- [ ] **Given** a node's memory usage exceeds 90%, **When** the threshold is crossed, **Then** an alert is triggered
- [ ] **Given** an alert is triggered, **When** the alert payload is assembled, **Then** it includes: node name, condition, resource usage

## Technical Notes

- Use Prometheus node-exporter + kube-state-metrics for node metrics
- Alert rule for NotReady: `kube_node_status_condition{condition="Ready",status="true"} == 0`
- Alert rule for disk: `node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.15`
- Alert rule for memory: `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes < 0.10`
- Notification delivery via Slack or email (same channel as pod alerts)

## Dependencies

### Requires
- 004-pod-alerting

### Enables
- 006-rollout-procedure

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Node recovers before alert fires | Alert is suppressed if condition resolves within the evaluation window |
| Multiple nodes fail simultaneously | Each node generates a separate alert with its own condition details |
| Disk usage fluctuates around threshold | Alert uses sustained threshold breach (e.g., 5-minute average) to avoid flapping |

## Out of Scope

- Automatic node replacement or scaling (covered by cluster autoscaler separately)
- Pod-level alerting (covered in 004-pod-alerting)

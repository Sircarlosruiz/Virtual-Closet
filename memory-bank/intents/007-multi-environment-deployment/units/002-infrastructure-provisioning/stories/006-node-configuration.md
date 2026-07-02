---
id: 006-node-configuration
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 006-Node Configuration

## User Story

**As a** devops engineer  
**I want** to configure node labels and taints  
**So that** workloads are scheduled on appropriate nodes

## Acceptance Criteria

- [ ] **Given** the control plane node, **When** inspecting labels, **Then** it has `role=control-plane` label
- [ ] **Given** the worker node, **When** inspecting labels, **Then** it has `role=worker` label
- [ ] **Given** the control plane node, **When** inspecting taints, **Then** taints prevent stateful workloads from being scheduled on it
- [ ] **Given** the cluster, **When** running `kubectl get nodes --show-labels`, **Then** all labels are verified and correct

## Technical Notes

- Use `kubectl label` and `kubectl taint` commands or Terraform kubernetes provider
- Control plane taint: `node-role.kubernetes.io/control-plane:NoSchedule`
- Labels should be applied via k3s server/agent configuration or post-provisioning
- Taints ensure workloads run on worker nodes only

## Dependencies

### Requires
- 005-k3s-worker

### Enables
- 007-persistent-volumes

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Label already exists | Terraform idempotent, no error |
| Taint conflicts | Existing taints preserved or updated |
| Node not ready | Labels/taints applied once node is Ready |

## Out of Scope

- Dynamic label management
- Node auto-labeling based on hardware

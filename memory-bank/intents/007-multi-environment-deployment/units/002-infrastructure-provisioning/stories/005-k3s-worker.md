---
id: 005-k3s-worker
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 005-K3s Worker

## User Story

**As a** devops engineer  
**I want** to provision a CX31 worker node joined to the k3s cluster  
**So that** workloads have dedicated compute resources

## Acceptance Criteria

- [ ] **Given** Terraform apply completes, **When** checking Hetzner Cloud, **Then** a CX31 server is provisioned
- [ ] **Given** the server is running, **When** inspecting k3s agent logs, **Then** the agent has joined the cluster successfully
- [ ] **Given** the node is registered, **When** running `kubectl get nodes`, **Then** the node shows `Ready` status
- [ ] **Given** the node is registered, **When** inspecting labels, **Then** the node is labeled as worker
- [ ] **Given** the worker node, **When** checking connectivity, **Then** it can reach the control plane API endpoint

## Technical Notes

- Use `hcloud_server` resource with type `cx31`
- k3s agent installation via cloud-init with `K3S_URL` and `K3S_TOKEN`
- Worker node should not run control plane components
- Node token retrieved from control plane during provisioning

## Dependencies

### Requires
- 004-k3s-control-plane

### Enables
- 006-node-configuration

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Worker fails to join cluster | k3s agent logs show connection error |
| Control plane unreachable | Worker retries connection with backoff |
| Node token expired | Regenerate token and reconfigure worker |

## Out of Scope

- Multiple worker nodes (single worker for now)
- Worker node auto-scaling

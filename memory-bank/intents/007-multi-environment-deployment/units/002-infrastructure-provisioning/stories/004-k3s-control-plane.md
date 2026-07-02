---
id: 004-k3s-control-plane
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 004-K3s Control Plane

## User Story

**As a** devops engineer  
**I want** to provision a CX21 control plane node running k3s  
**So that** the cluster has a management plane

## Acceptance Criteria

- [ ] **Given** Terraform apply completes, **When** checking Hetzner Cloud, **Then** a CX21 server is provisioned
- [ ] **Given** the server is running, **When** SSH-ing into the node, **Then** k3s service is active and running
- [ ] **Given** k3s is installed, **When** running `kubectl get nodes` from the control plane, **Then** kubectl can connect to the cluster API
- [ ] **Given** the node is registered, **When** inspecting labels, **Then** the node is labeled as control-plane
- [ ] **Given** the server specification, **When** inspecting the instance, **Then** the server type is CX21

## Technical Notes

- Use `hcloud_server` resource with type `cx21`
- k3s installation via cloud-init or user-data script
- Control plane node should run with `--disable-agent` flag if dedicated
- kubeconfig should be extracted and stored securely

## Dependencies

### Requires
- 003-hcloud-vpc

### Enables
- 005-k3s-worker

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| k3s installation fails | Cloud-init logs available for debugging |
| Server provisioning timeout | Terraform retries or fails with clear error |
| kubeconfig extraction fails | Manual retrieval procedure documented |

## Out of Scope

- High availability control plane (single node for now)
- Control plane node scaling

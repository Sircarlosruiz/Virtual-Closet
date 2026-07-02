---
id: 003-hcloud-vpc
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 003-Hcloud VPC

## User Story

**As a** devops engineer  
**I want** to provision a Hetzner VPC with networking  
**So that** the cluster has isolated network connectivity

## Acceptance Criteria

- [ ] **Given** Terraform apply completes, **When** checking Hetzner Cloud console, **Then** a VPC network is created in the configured region
- [ ] **Given** the VPC is provisioned, **When** inspecting firewall rules, **Then** SSH (22), k3s API (6443), and application ports are allowed
- [ ] **Given** the network is created, **When** inspecting attachments, **Then** the network is attached to both control plane and worker nodes
- [ ] **Given** the Terraform configuration, **When** running `terraform plan`, **Then** it applies cleanly with no errors

## Technical Notes

- Use `hcloud_network` and `hcloud_network_subnet` resources
- Firewall rules should use `hcloud_firewall` resource
- Subnet IP range should accommodate cluster growth (e.g., 10.0.0.0/16)

## Dependencies

### Requires
- 002-terraform-variables

### Enables
- 004-k3s-control-plane

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| VPC already exists | Terraform imports or errors with clear message |
| Firewall rule conflict | Terraform plan shows diff, apply resolves |
| Subnet IP exhaustion | Terraform validates CIDR range at plan time |

## Out of Scope

- Multi-region networking
- VPN or peering configurations

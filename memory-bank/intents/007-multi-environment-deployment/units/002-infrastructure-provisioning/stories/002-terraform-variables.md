---
id: 002-terraform-variables
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 002-Terraform Variables

## User Story

**As a** devops engineer  
**I want** centralized Terraform variables and outputs  
**So that** configuration is parameterized and reusable across environments

## Acceptance Criteria

- [ ] **Given** the project root, **When** inspecting `variables.tf`, **Then** all configurable inputs are defined including region, server types, and k3s token
- [ ] **Given** the project root, **When** inspecting `outputs.tf`, **Then** cluster endpoint and node IPs are exposed
- [ ] **Given** the project root, **When** inspecting the directory, **Then** a `.tfvars.example` file is provided with sample values
- [ ] **Given** sensitive variables like k3s token, **When** inspecting their definitions, **Then** they are marked with `sensitive = true`

## Technical Notes

- Use `variable` blocks with type constraints and descriptions
- Outputs should use `sensitive` attribute where appropriate
- `.tfvars.example` should not contain real credentials

## Dependencies

### Requires
- 001-terraform-structure

### Enables
- 003-hcloud-vpc

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Missing required variable | Terraform plan fails with clear validation error |
| Invalid variable type | Terraform validates and rejects with type mismatch error |
| Sensitive value in output | Value is masked in CLI output and state inspection |

## Out of Scope

- Environment-specific `.tfvars` files with real values
- Variable validation rules beyond type checking

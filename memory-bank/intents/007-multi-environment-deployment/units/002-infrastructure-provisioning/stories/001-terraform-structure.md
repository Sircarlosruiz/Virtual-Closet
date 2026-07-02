---
id: 001-terraform-structure
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 001-Terraform Structure

## User Story

**As a** devops engineer  
**I want** a well-organized Terraform project structure with modules for hcloud  
**So that** infrastructure is modular and reusable

## Acceptance Criteria

- [ ] **Given** the Terraform project root, **When** inspecting the directory structure, **Then** a `modules/` directory exists containing `vpc`, `k3s`, and `backup` subdirectories
- [ ] **Given** any module directory, **When** inspecting its contents, **Then** `variables.tf` and `outputs.tf` files are present
- [ ] **Given** the project root, **When** inspecting `main.tf`, **Then** it composes all modules via `module` blocks
- [ ] **Given** the project, **When** a new team member onboards, **Then** the directory structure is documented in a README or inline comments

## Technical Notes

- Use Terraform 1.5+ with hcloud provider
- Each module should be self-contained with its own variables, outputs, and resources
- Root `main.tf` should only contain module composition and provider configuration

## Dependencies

### Requires
- None

### Enables
- 002-terraform-variables

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Module directory missing | Terraform plan fails with clear error |
| Circular module dependency | Terraform validates and rejects with error message |
| Unused module in root | No resources created, no error |

## Out of Scope

- Writing module implementations (covered by downstream stories)
- CI/CD pipeline for Terraform

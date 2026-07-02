---
id: 010-secrets-template
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 010-Secrets Template

## User Story

**As a** devops engineer  
**I want** a k8s Secrets template  
**So that** CI/CD can populate secrets without exposing them in manifests

## Acceptance Criteria

- [ ] **Given** the manifest structure exists, **When** I create the secrets template, **Then** a Secret template for database credentials is defined
- [ ] **Given** the manifest structure exists, **When** I create the secrets template, **Then** a Secret template for MinIO credentials is defined
- [ ] **Given** the manifest structure exists, **When** I create the secrets template, **Then** a Secret template for JWT signing key is defined
- [ ] **Given** the manifest structure exists, **When** I create the secrets template, **Then** a Secret template for API keys is defined
- [ ] **Given** the secrets template, **When** I review the values, **Then** the template uses placeholder values (base64 encoded)
- [ ] **Given** the secrets template, **When** I review documentation, **Then** CI/CD instructions for populating secrets are documented

## Technical Notes

- Secrets use type: Opaque with base64-encoded values
- Placeholder values should be clearly marked (e.g., "REPLACE_ME_BASE64")
- CI/CD pipeline should inject real values from a secrets manager (e.g., AWS Secrets Manager, Vault)
- Never commit real secret values to the repository

## Dependencies

### Requires
- 001-manifest-structure

### Enables
- 016-manifest-validation

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Secret not populated before deployment | Pods fail to start; containers exit with missing env var error |
| Base64 encoding incorrect | Secret created but value decoded incorrectly; application fails to authenticate |
| Secret rotated mid-deployment | Old pods use old secret; new pods use new secret; may cause auth mismatch |

## Out of Scope

- External secrets manager integration (Vault, AWS Secrets Manager)
- Secret rotation automation
- Encryption at rest for etcd

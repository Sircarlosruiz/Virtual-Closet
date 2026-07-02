---
id: 016-manifest-validation
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 016-Manifest Validation

## User Story

**As a** devops engineer  
**I want** to validate all Kubernetes manifests  
**So that** there are no syntax or schema errors before deployment

## Acceptance Criteria

- [ ] **Given** all manifests are created, **When** I run validation, **Then** all YAML files pass kubectl apply --dry-run=client
- [ ] **Given** all manifests are created, **When** I run validation, **Then** there are no schema errors
- [ ] **Given** all manifests are created, **When** I run validation, **Then** there are no missing required fields
- [ ] **Given** all manifests are created, **When** I run validation, **Then** cross-references are valid (Services match Deployments, etc.)
- [ ] **Given** all manifests are validated, **When** I review CI/CD, **Then** a validation script or CI step is created

## Technical Notes

- kubectl apply --dry-run=client validates locally without contacting the cluster
- Cross-reference validation: Service selectors match Deployment labels, ConfigMap/Secret names exist
- Validation script should iterate over all YAML files in the k8s directory
- Consider using kubeval or kubeconform for additional schema validation

## Dependencies

### Requires
- 002-frontend-deployment
- 003-backend-deployment
- 004-postgresql-statefulset
- 005-minio-statefulset
- 006-rabbitmq-statefulset
- 007-celery-deployment
- 008-service-definitions
- 009-ingress-configuration
- 010-secrets-template
- 011-configmaps
- 012-liveness-probes
- 013-readiness-probes
- 014-resource-limits
- 015-rbac-policies

### Enables
- 017-dry-run-deployment

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Manifest references non-existent ConfigMap | dry-run=client may pass; dry-run=server fails |
| YAML syntax error in one file | Validation fails; error message indicates file and line number |
| Kubernetes API version not supported by cluster | dry-run=client may pass; dry-run=server fails with API version error |

## Out of Scope

- Automated manifest generation (Helm, Kustomize build)
- Policy enforcement (OPA, Kyverno)
- Manifest linting for best practices (pluto, popeye)

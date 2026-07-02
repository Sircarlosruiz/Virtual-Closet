---
id: 001-manifest-structure
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 001-Manifest Structure

## User Story

**As a** devops engineer  
**I want** a well-organized Kubernetes manifest folder structure  
**So that** manifests are maintainable and easy to navigate

## Acceptance Criteria

- [ ] **Given** the k8s directory does not exist, **When** I create the folder structure, **Then** the following directories exist: k8s/{base,overlays}/{frontend,backend,postgres,minio,rabbitmq,celery}
- [ ] **Given** the folder structure is created, **When** I review the organization, **Then** Kustomize or plain YAML organization is documented
- [ ] **Given** the folder structure is created, **When** I review namespaces, **Then** staging and production namespace separation is defined
- [ ] **Given** the folder structure is created, **When** I read the README, **Then** the structure is fully explained

## Technical Notes

- Kustomize overlays enable environment-specific configuration without duplicating base manifests
- Namespace per environment prevents resource collision between staging and production
- Each component folder contains its own deployment, service, and config manifests

## Dependencies

### Requires
- None

### Enables
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
- 016-manifest-validation
- 017-dry-run-deployment
- 018-deployment-docs

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Team member adds a new service | They can follow the existing folder pattern and add a new component directory |
| Environment-specific override needed | Overlay directory contains only the diff from base |
| Manifests applied to wrong namespace | Namespace is explicitly set in each manifest, preventing accidental default namespace usage |

## Out of Scope

- Helm chart creation
- CI/CD pipeline configuration for applying manifests
- Cluster provisioning or infrastructure setup

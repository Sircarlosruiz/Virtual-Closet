---
id: 002-frontend-deployment
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 002-Frontend Deployment

## User Story

**As a** devops engineer  
**I want** a Kubernetes Deployment for the Next.js frontend  
**So that** the frontend runs with 2+ replicas

## Acceptance Criteria

- [ ] **Given** the manifest structure exists, **When** I create the frontend deployment, **Then** the Deployment specifies 2 replicas
- [ ] **Given** the deployment manifest, **When** I review the container spec, **Then** the container image is pulled from a private registry
- [ ] **Given** the deployment manifest, **When** I review the update strategy, **Then** it uses a rolling update with maxSurge: 1 and maxUnavailable: 0
- [ ] **Given** the deployment manifest, **When** I review environment variables, **Then** they are sourced from a ConfigMap and/or Secret
- [ ] **Given** the deployment manifest, **When** I review resource specs, **Then** resource requests and limits are defined

## Technical Notes

- Rolling update with maxUnavailable: 0 ensures zero-downtime deployments
- Private registry requires imagePullSecrets configuration
- Environment variables should reference ConfigMap for non-sensitive values and Secret for sensitive ones

## Dependencies

### Requires
- 001-manifest-structure

### Enables
- 008-service-definitions

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Image pull fails due to auth | imagePullSecrets references a valid registry credential Secret |
| Pod crashes during rollout | maxSurge: 1 keeps old pod running until new pod is ready |
| ConfigMap not yet created | Pod enters ContainerCreating until ConfigMap is available |

## Out of Scope

- Horizontal Pod Autoscaler configuration
- Ingress configuration (covered in 009)
- Frontend build or image creation

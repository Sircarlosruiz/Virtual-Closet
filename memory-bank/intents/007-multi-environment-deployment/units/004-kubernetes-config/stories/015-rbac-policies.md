---
id: 015-rbac-policies
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 015-RBAC Policies

## User Story

**As a** devops engineer  
**I want** RBAC policies and dedicated service accounts  
**So that** pods have minimal permissions

## Acceptance Criteria

- [ ] **Given** the manifest structure exists, **When** I create RBAC manifests, **Then** a ServiceAccount for the frontend is defined
- [ ] **Given** the manifest structure exists, **When** I create RBAC manifests, **Then** a ServiceAccount for the backend is defined
- [ ] **Given** the manifest structure exists, **When** I create RBAC manifests, **Then** a ServiceAccount for Celery is defined
- [ ] **Given** the ServiceAccounts exist, **When** I create Roles and RoleBindings, **Then** each service has a Role/RoleBinding with minimal permissions
- [ ] **Given** the deployments, **When** I review serviceAccountName, **Then** no deployment uses the default service account
- [ ] **Given** the RBAC policies, **When** I verify permissions, **Then** RBAC policies are verified with kubectl auth can-i

## Technical Notes

- Each ServiceAccount is referenced in the corresponding Deployment/StatefulSet spec.serviceAccountName
- Roles should be namespace-scoped (Role + RoleBinding), not cluster-scoped
- Most application pods need no special permissions; empty Role or no RoleBinding is acceptable
- Verify with: kubectl auth can-i --as=system:serviceaccount:{namespace}:{sa-name} {verb} {resource}

## Dependencies

### Requires
- 001-manifest-structure

### Enables
- 016-manifest-validation

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| ServiceAccount deleted while pod running | Pod continues running; new pods fail to schedule |
| RoleBinding references non-existent Role | Pod schedules but API calls fail with forbidden |
| Pod needs access to secrets in another namespace | Requires ClusterRole or cross-namespace RBAC (avoid if possible) |

## Out of Scope

- Pod Security Policies / Pod Security Standards
- Network policies for pod-to-pod communication
- OIDC or external authentication for kubectl access

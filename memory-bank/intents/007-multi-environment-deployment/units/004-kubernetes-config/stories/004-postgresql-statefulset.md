---
id: 004-postgresql-statefulset
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 004-PostgreSQL StatefulSet

## User Story

**As a** devops engineer  
**I want** a Kubernetes StatefulSet for PostgreSQL  
**So that** the database has stable identity and persistent storage

## Acceptance Criteria

- [ ] **Given** the manifest structure exists, **When** I create the PostgreSQL manifest, **Then** a StatefulSet with 1 replica is defined
- [ ] **Given** the StatefulSet manifest, **When** I review the volumeClaimTemplates, **Then** a PVC template for the data directory with minimum 20Gi is specified
- [ ] **Given** the StatefulSet manifest, **When** I review the container image, **Then** PostgreSQL 16 image is used
- [ ] **Given** the StatefulSet manifest, **When** I review credentials, **Then** the password is sourced from a Secret
- [ ] **Given** the StatefulSet is running, **When** a pod restarts, **Then** data persists across pod restarts via the PVC
- [ ] **Given** the StatefulSet manifest, **When** I review services, **Then** a headless Service is defined for stable DNS access

## Technical Notes

- Headless Service (clusterIP: None) provides stable pod DNS: postgres-0.postgres.{namespace}.svc.cluster.local
- volumeClaimTemplates ensure each pod gets its own persistent volume
- PostgreSQL data directory should be mounted at /var/lib/postgresql/data

## Dependencies

### Requires
- 001-manifest-structure

### Enables
- 008-service-definitions

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| PVC provisioning fails | Pod stays in Pending; StatefulSet does not create next pod |
| Pod rescheduled to different node | PVC reattaches to new node; data remains intact |
| Storage class not available | PVC stays in Pending; pod never starts |

## Out of Scope

- PostgreSQL backup and recovery automation
- Read replica configuration
- Database schema migrations

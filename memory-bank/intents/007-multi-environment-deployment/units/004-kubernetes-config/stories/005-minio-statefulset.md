---
id: 005-minio-statefulset
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 005-MinIO StatefulSet

## User Story

**As a** devops engineer  
**I want** a Kubernetes StatefulSet for MinIO  
**So that** object storage has persistent volumes

## Acceptance Criteria

- [ ] **Given** the manifest structure exists, **When** I create the MinIO manifest, **Then** a StatefulSet with 1 replica is defined
- [ ] **Given** the StatefulSet manifest, **When** I review the volumeClaimTemplates, **Then** a PVC template for data with minimum 50Gi is specified
- [ ] **Given** the StatefulSet manifest, **When** I review the container image, **Then** a MinIO image is used
- [ ] **Given** the StatefulSet manifest, **When** I review credentials, **Then** access key and secret key are sourced from a Secret
- [ ] **Given** the StatefulSet is running, **When** a pod restarts, **Then** data persists across pod restarts via the PVC
- [ ] **Given** the StatefulSet manifest, **When** I review services, **Then** a Service for API access is defined

## Technical Notes

- MinIO API runs on port 9000, Console on port 9001
- Access key and secret key are set via MINIO_ROOT_USER and MINIO_ROOT_PASSWORD environment variables
- Data directory should be mounted at /data

## Dependencies

### Requires
- 001-manifest-structure

### Enables
- 008-service-definitions

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| PVC provisioning fails | Pod stays in Pending; MinIO is unavailable |
| Pod rescheduled to different node | PVC reattaches; stored objects remain accessible |
| MinIO credentials rotated | Secret updated; pod restarted to pick up new credentials |

## Out of Scope

- MinIO bucket lifecycle policies
- Multi-node MinIO cluster setup
- MinIO gateway mode

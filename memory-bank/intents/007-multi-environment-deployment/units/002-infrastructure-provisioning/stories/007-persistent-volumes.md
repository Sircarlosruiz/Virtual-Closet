---
id: 007-persistent-volumes
unit: 002-infrastructure-provisioning
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 002-infrastructure-provisioning
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 007-Persistent Volumes

## User Story

**As a** devops engineer  
**I want** persistent volume provisioning configured  
**So that** stateful services (PostgreSQL, MinIO, RabbitMQ) have durable storage

## Acceptance Criteria

- [ ] **Given** the cluster, **When** inspecting storage provisioners, **Then** local-path-provisioner or equivalent is installed
- [ ] **Given** the provisioner is installed, **When** inspecting StorageClasses, **Then** a default StorageClass is created and marked as default
- [ ] **Given** a PVC is created, **When** inspecting its status, **Then** the PVC binds successfully to a PV
- [ ] **Given** a pod using a PVC, **When** the pod is restarted, **Then** data persists across restarts
- [ ] **Given** the storage setup, **When** deploying a sample pod with PVC, **Then** the pod runs successfully with persistent data

## Technical Notes

- k3s includes local-path-provisioner by default
- StorageClass should be configured with `reclaimPolicy: Retain` for data safety
- PVCs for PostgreSQL, MinIO, RabbitMQ should request appropriate sizes
- Test with a simple pod writing to the volume

## Dependencies

### Requires
- 006-node-configuration

### Enables
- 008-backup-cronjob

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Node disk full | Provisioner reports error, pod pending |
| PVC deleted | PV retained based on reclaim policy |
| Provisioner pod crashes | Existing volumes remain accessible |

## Out of Scope

- Network-attached storage (NAS)
- Volume snapshots and cloning

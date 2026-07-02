---
id: 006-rabbitmq-statefulset
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 006-RabbitMQ StatefulSet

## User Story

**As a** devops engineer  
**I want** a Kubernetes StatefulSet for RabbitMQ  
**So that** the message queue has persistent storage and stable identity

## Acceptance Criteria

- [ ] **Given** the manifest structure exists, **When** I create the RabbitMQ manifest, **Then** a StatefulSet with 1 replica is defined
- [ ] **Given** the StatefulSet manifest, **When** I review the volumeClaimTemplates, **Then** a PVC template for data with minimum 10Gi is specified
- [ ] **Given** the StatefulSet manifest, **When** I review the container image, **Then** a RabbitMQ image is used
- [ ] **Given** the StatefulSet manifest, **When** I review credentials, **Then** username and password are sourced from a Secret
- [ ] **Given** the StatefulSet is running, **When** a pod restarts, **Then** messages persist across pod restarts via the PVC
- [ ] **Given** the StatefulSet manifest, **When** I review plugins, **Then** the management plugin is enabled

## Technical Notes

- RabbitMQ management plugin enabled via RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS or enabled_plugins file
- AMQP port: 5672, Management UI port: 15672
- Data directory: /var/lib/rabbitmq/mnesia

## Dependencies

### Requires
- 001-manifest-structure

### Enables
- 008-service-definitions

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| PVC provisioning fails | Pod stays in Pending; message queue unavailable |
| Pod rescheduled to different node | PVC reattaches; queued messages remain intact |
| RabbitMQ credentials changed | Secret updated; pod restarted to apply new credentials |

## Out of Scope

- RabbitMQ cluster with multiple nodes
- RabbitMQ shovel or federation configuration
- Queue definition and message schema design

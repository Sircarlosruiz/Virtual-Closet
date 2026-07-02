---
id: 008-service-definitions
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 008-Service Definitions

## User Story

**As a** devops engineer  
**I want** Kubernetes Service definitions for all services  
**So that** pods can communicate internally

## Acceptance Criteria

- [ ] **Given** all deployments and statefulsets are defined, **When** I create service manifests, **Then** a ClusterIP Service for the frontend is defined
- [ ] **Given** all deployments and statefulsets are defined, **When** I create service manifests, **Then** a ClusterIP Service for the backend is defined
- [ ] **Given** the PostgreSQL StatefulSet is defined, **When** I create its service, **Then** a headless Service (clusterIP: None) is defined
- [ ] **Given** the MinIO StatefulSet is defined, **When** I create its service, **Then** a ClusterIP Service for MinIO is defined
- [ ] **Given** the RabbitMQ StatefulSet is defined, **When** I create its service, **Then** a ClusterIP Service for RabbitMQ is defined
- [ ] **Given** all services are defined, **When** I review port mappings, **Then** port mappings are correct for all services

## Technical Notes

- Frontend Service: port 80 -> targetPort 3000
- Backend Service: port 8000 -> targetPort 8000
- PostgreSQL headless Service: port 5432 -> targetPort 5432
- MinIO Service: port 9000 -> targetPort 9000 (API), port 9001 -> targetPort 9001 (Console)
- RabbitMQ Service: port 5672 -> targetPort 5672 (AMQP), port 15672 -> targetPort 15672 (Management)

## Dependencies

### Requires
- 002-frontend-deployment
- 003-backend-deployment
- 004-postgresql-statefulset
- 005-minio-statefulset
- 006-rabbitmq-statefulset
- 007-celery-deployment

### Enables
- 009-ingress-configuration

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Service selector doesn't match any pod | Service has no endpoints; connections fail with connection refused |
| Port mapping incorrect | Traffic routed to wrong port; connection timeout or refused |
| Headless service used for non-StatefulSet | Returns multiple A records; may cause unexpected behavior |

## Out of Scope

- External LoadBalancer services
- Service mesh configuration (Istio, Linkerd)
- Network policies for service-to-service communication

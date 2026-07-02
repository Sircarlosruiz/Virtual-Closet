---
id: 014-resource-limits
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 014-Resource Limits

## User Story

**As a** devops engineer  
**I want** resource requests and limits for all pods  
**So that** the cluster uses resources efficiently

## Acceptance Criteria

- [ ] **Given** the frontend deployment, **When** I review resources, **Then** requests are 500m CPU / 512Mi memory, limits are 1000m CPU / 1Gi memory
- [ ] **Given** the backend deployment, **When** I review resources, **Then** requests are 1000m CPU / 1Gi memory, limits are 2000m CPU / 2Gi memory
- [ ] **Given** the PostgreSQL StatefulSet, **When** I review resources, **Then** requests are 500m CPU / 1Gi memory, limits are 1000m CPU / 2Gi memory
- [ ] **Given** the MinIO StatefulSet, **When** I review resources, **Then** requests are 250m CPU / 512Mi memory, limits are 500m CPU / 1Gi memory
- [ ] **Given** the RabbitMQ StatefulSet, **When** I review resources, **Then** requests are 250m CPU / 256Mi memory, limits are 500m CPU / 512Mi memory
- [ ] **Given** the Celery deployment, **When** I review resources, **Then** requests are 500m CPU / 512Mi memory, limits are 1000m CPU / 1Gi memory

## Technical Notes

- Requests: guaranteed resources for scheduling; pod is evicted if node is under pressure and pod is below request
- Limits: maximum resources; container is OOMKilled if memory limit exceeded, CPU throttled if CPU limit exceeded
- Backend has higher limits due to FastAPI + database connection overhead
- PostgreSQL and MinIO need sufficient memory for caching and file operations

## Dependencies

### Requires
- 002-frontend-deployment
- 003-backend-deployment
- 004-postgresql-statefulset
- 005-minio-statefulset
- 006-rabbitmq-statefulset
- 007-celery-deployment

### Enables
- 016-manifest-validation

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Container exceeds memory limit | Container OOMKilled; pod restarts; may enter CrashLoopBackOff |
| Container exceeds CPU limit | CPU throttled; application slows down but not killed |
| Requests too high for cluster capacity | Pod stays in Pending; insufficient resources to schedule |

## Out of Scope

- LimitRange and ResourceQuota for namespace-level constraints
- Vertical Pod Autoscaler for automatic resource tuning
- Monitoring and alerting for resource usage

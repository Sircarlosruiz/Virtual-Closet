---
unit: 004-kubernetes-config
unit_type: infrastructure
default_bolt_type: ddd-construction-bolt
intent: 007-multi-environment-deployment
created: 2026-06-17T14:42:00Z
---

# Unit Brief: Kubernetes Deployment Configuration

## Purpose

Create comprehensive Kubernetes manifests for all services (frontend, backend, PostgreSQL, MinIO, RabbitMQ, Celery worker) with proper networking, secrets, health probes, and resource management.

## Scope

**In Scope**:
- Deployment manifests for frontend (2+ replicas)
- Deployment manifests for backend (2+ replicas)
- StatefulSet for PostgreSQL with persistent volumes
- StatefulSet for MinIO with persistent volumes
- StatefulSet for RabbitMQ with persistent volumes
- Deployment for Celery worker with auto-scaling hints
- Service definitions for all services
- Ingress configuration for external access
- k8s Secrets for sensitive data
- ConfigMaps for environment configuration
- Liveness and readiness probes
- Resource requests and limits
- RBAC policies (service accounts, role bindings)

**Out of Scope**:
- Container images (Unit 3)
- CI/CD automation (Unit 6)
- Monitoring and observability (Unit 7)

## Key Decisions

1. **Manifest Organization**: Separate files per service (maintainability)
2. **StatefulSets for Stateful**: PostgreSQL, MinIO, RabbitMQ use StatefulSets
3. **Replicas**: Frontend/Backend 2+ replicas, Database 1 primary
4. **Health Probes**: Liveness every 10s, readiness for traffic control
5. **Resources**: Memory + CPU limits per pod (prevent node overload)

## Acceptance Criteria

- [ ] Frontend Deployment manifest created (2+ replicas)
- [ ] Backend Deployment manifest created (2+ replicas)
- [ ] PostgreSQL StatefulSet manifest created
- [ ] MinIO StatefulSet manifest created
- [ ] RabbitMQ StatefulSet manifest created
- [ ] Celery worker Deployment manifest created
- [ ] Service definitions for all services created
- [ ] Ingress controller configured and routing rules set
- [ ] k8s Secrets template created (for CI/CD to populate)
- [ ] ConfigMaps created for environment variables
- [ ] Liveness probes configured for all services
- [ ] Readiness probes configured for all services
- [ ] Resource requests/limits defined and tested
- [ ] RBAC policies implemented and verified
- [ ] All manifests validated (kubectl validate)
- [ ] Dry-run deployment successful

## Stories

1. Design k8s manifest folder structure
2. Create frontend Deployment manifest
3. Create backend Deployment manifest
4. Create PostgreSQL StatefulSet manifest
5. Create MinIO StatefulSet manifest
6. Create RabbitMQ StatefulSet manifest
7. Create Celery worker Deployment manifest
8. Create Service manifests for all services
9. Configure Ingress controller and routing
10. Create k8s Secrets template
11. Create ConfigMaps for environment variables
12. Implement liveness probes (all services)
13. Implement readiness probes (all services)
14. Define resource requests and limits
15. Implement RBAC policies and service accounts
16. Validate manifests (kubectl validate)
17. Test dry-run deployment
18. Document manifest deployment procedure

## Deliverables

- Kubernetes YAML manifests (organized by service)
- Ingress configuration
- Secrets template (for CI/CD)
- ConfigMap examples
- Health probe implementations
- RBAC policies
- Deployment documentation and runbook

## Dependencies

- Depends on: Unit 2 (Infrastructure), Unit 3 (Container Optimization)
- Depended by: Unit 6 (CI/CD), Unit 7 (Observability)

## Effort Estimate

**5-7 days** (manifests + probes + RBAC + testing)

## Risk Factors

- Risk: Resource limits too low → pod evictions
  - Mitigation: Monitor resource usage during testing, adjust limits
- Risk: Readiness probes fail due to slow startup
  - Mitigation: Tune probe timeouts based on actual startup time
- Risk: StatefulSet data loss if PVC deleted
  - Mitigation: Document persistent volume backup and recovery

## Notes

- All manifests must be validated before deployment
- Resource limits should be monitored and adjusted post-deployment
- RBAC follows principle of least privilege
- ConfigMaps and Secrets separated for security

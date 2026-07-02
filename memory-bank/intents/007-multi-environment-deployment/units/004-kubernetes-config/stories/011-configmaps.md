---
id: 011-configmaps
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 011-ConfigMaps

## User Story

**As a** devops engineer  
**I want** ConfigMaps for non-sensitive configuration  
**So that** environment-specific settings are separated from code

## Acceptance Criteria

- [ ] **Given** the manifest structure exists, **When** I create ConfigMaps, **Then** a ConfigMap for the frontend is defined with NEXT_PUBLIC_API_URL and similar variables
- [ ] **Given** the manifest structure exists, **When** I create ConfigMaps, **Then** a ConfigMap for the backend is defined with DATABASE_URL, MINIO_ENDPOINT, RABBITMQ_URL, etc.
- [ ] **Given** the ConfigMaps, **When** I review values across environments, **Then** values differ per environment (staging vs production)
- [ ] **Given** the ConfigMaps, **When** I review documentation, **Then** the ConfigMap is documented with all keys and their purposes

## Technical Notes

- Frontend ConfigMap: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_APP_NAME, etc.
- Backend ConfigMap: DATABASE_URL, MINIO_ENDPOINT, MINIO_BUCKET, RABBITMQ_URL, CELERY_BROKER_URL, etc.
- Environment-specific values managed via Kustomize overlays or separate ConfigMap files per environment
- ConfigMaps are mounted as environment variables or files

## Dependencies

### Requires
- 001-manifest-structure

### Enables
- 016-manifest-validation

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| ConfigMap updated while pods running | Pods do not automatically pick up changes; requires rollout restart |
| ConfigMap key missing | Pod starts but environment variable is empty; application may fail |
| ConfigMap value contains special characters | Value must be properly escaped in YAML |

## Out of Scope

- Dynamic configuration reloading without restart
- Configuration validation at application startup
- ConfigMap versioning or rollback

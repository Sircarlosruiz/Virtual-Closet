---
id: 009-ingress-configuration
unit: 004-kubernetes-config
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
assigned_bolt: 004-kubernetes-config
implemented: true
completed: 2026-07-01T00:00:00Z
---

# Story: 009-Ingress Configuration

## User Story

**As a** devops engineer  
**I want** an Ingress configuration for external access  
**So that** users can reach the frontend and API

## Acceptance Criteria

- [ ] **Given** all services are defined, **When** I create the Ingress manifest, **Then** an Ingress resource is created
- [ ] **Given** the Ingress manifest, **When** I review the rules, **Then** routes / to the frontend Service
- [ ] **Given** the Ingress manifest, **When** I review the rules, **Then** routes /api/ to the backend Service
- [ ] **Given** the Ingress manifest, **When** I review TLS, **Then** TLS termination is configured
- [ ] **Given** the Ingress manifest, **When** I review the class, **Then** an Ingress class is specified (e.g., nginx)
- [ ] **Given** the Ingress manifest, **When** I review the host, **Then** the hostname is configurable per environment

## Technical Notes

- Ingress class: nginx (or cloud-provider specific)
- TLS certificate can be managed via cert-manager or manually
- Path-based routing: / -> frontend, /api/ -> backend
- Hostname differs between staging and production environments

## Dependencies

### Requires
- 008-service-definitions

### Enables
- 016-manifest-validation

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| TLS secret not found | Ingress controller may serve default certificate or reject connections |
| Path prefix conflict (/api vs /api/) | Rewrite rules or exact path matching needed to avoid ambiguity |
| Ingress class not available in cluster | Ingress resource created but not functional; no external access |

## Out of Scope

- cert-manager auto-provisioning
- Rate limiting or WAF configuration
- WebSocket proxy configuration

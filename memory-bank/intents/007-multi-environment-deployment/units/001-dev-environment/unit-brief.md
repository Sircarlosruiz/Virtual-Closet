---
unit: 001-dev-environment
unit_type: infrastructure
default_bolt_type: ddd-construction-bolt
intent: 007-multi-environment-deployment
created: 2026-06-17T14:42:00.000Z
status: complete
---

# Unit Brief: Development Environment Setup

## Purpose

Refactor and optimize docker-compose.yml for local development with all required services, removing obsolete components and supporting GPU-enabled AI models.

## Scope

**In Scope**:
- Refactor docker-compose.yml to remove catvton service and catvton_cache volume
- Ensure single `docker-compose up` starts all dev services
- Configure automatic Alembic migrations on startup
- Enable hot-reload for Next.js frontend and FastAPI backend
- Support GPU inference for fashn/flux models
- Document .env setup with .env.example template

**Out of Scope**:
- Production-ready configurations (handled in Unit 4)
- Kubernetes-specific settings
- CI/CD pipelines

## Key Decisions

1. **Separation**: Maintain dev docker-compose separate from k8s production manifests
2. **GPU Support**: Keep GPU support for local AI model testing (fashn, flux)
3. **Zero Infrastructure**: All services run locally via Docker, no external dependencies for dev

## Acceptance Criteria

- [ ] docker-compose.yml refactored (catvton removed)
- [ ] All services start via single `docker-compose up`
- [ ] Alembic auto-runs migrations on PostgreSQL startup
- [ ] Frontend hot-reload working (Next.js)
- [ ] Backend hot-reload working (FastAPI)
- [ ] .env.example created and documented
- [ ] GPU support validated for fashn/flux (optional: local GPU available)
- [ ] Local development guide created

## Stories

1. Refactor docker-compose.yml structure (remove catvton)
2. Configure Alembic auto-migration on startup
3. Add hot-reload for frontend (Next.js)
4. Add hot-reload for backend (FastAPI)
5. Create and document .env.example
6. Test full dev environment startup
7. Document local development quick-start guide

## Deliverables

- Refactored docker-compose.yml
- .env.example file
- Local development guide (README)
- Validated working dev environment

## Dependencies

- Depends on: None (foundation)
- Depended by: None directly

## Effort Estimate

**3-5 days** (refactoring + testing + documentation)

## Risk Factors

- Risk: Removing catvton might break existing workflows if still in use
  - Mitigation: Verify no active catvton usage before removal
- Risk: Docker Compose version compatibility issues
  - Mitigation: Document required Docker Compose version in README

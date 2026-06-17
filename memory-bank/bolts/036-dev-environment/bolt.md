---
id: 036-dev-environment
unit: 001-dev-environment
intent: 007-multi-environment-deployment
type: ddd-construction-bolt
status: planned
stories:
  - 001-refactor-docker-compose
  - 002-configure-alembic-auto
  - 003-hot-reload-frontend
  - 004-hot-reload-backend
  - 005-env-example
  - 006-test-dev-startup
  - 007-dev-guide
created: 2026-06-17T15:05:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts: []
enables_bolts: []
requires_units: []
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 036-dev-environment

## Overview

Refactor and optimize docker-compose.yml for local development, removing obsolete components (catvton), and enabling hot-reload for both frontend and backend. This is the foundation bolt for the entire deployment strategy, ensuring developers have a smooth local dev experience.

## Objective

Create a clean, efficient local development environment that starts with single `docker-compose up`, includes automatic database migrations, and enables hot-reload for rapid iteration on both frontend and backend code.

## Stories Included

- **001-refactor-docker-compose**: Refactor and clean docker-compose.yml (Must)
- **002-configure-alembic-auto**: Auto-run Alembic migrations on startup (Must)
- **003-hot-reload-frontend**: Enable Next.js hot-reload (Must)
- **004-hot-reload-backend**: Enable FastAPI hot-reload (Must)
- **005-env-example**: Create .env.example template (Must)
- **006-test-dev-startup**: Validate full environment startup (Must)
- **007-dev-guide**: Document quick-start guide (Should)

## Bolt Type

**Type**: DDD Construction Bolt  
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Model**: Design docker-compose architecture, identify removals → bolt-036-01-domain-model.md
- [ ] **2. Design**: Technical specification for hot-reload, migration automation → bolt-036-02-technical-design.md
- [ ] **3. Implement**: Code changes to docker-compose.yml, scripts, documentation
- [ ] **4. Test**: Validation on clean environment, documentation review → bolt-036-03-test-report.md

## Dependencies

### Requires
- None (foundation bolt)

### Enables
- Bolt 004: k8s configuration (depends on validated dev setup)
- Bolt 005: DB migrations (depends on dev environment)
- Bolt 006: CI/CD (depends on dev environment validation)

## Success Criteria

- [ ] docker-compose.yml refactored and validated
- [ ] Alembic auto-migration working on startup
- [ ] Hot-reload enabled for frontend (Next.js)
- [ ] Hot-reload enabled for backend (FastAPI)
- [ ] .env.example created with documentation
- [ ] Full environment starts successfully
- [ ] Local development guide complete
- [ ] All tests passing
- [ ] Code reviewed and merged

## Acceptance Criteria Summary

**For each story**:
- All acceptance criteria from story definition met
- Documentation updated
- Tests passing
- Peer review complete

## Complexity Assessment

- **Complexity**: Medium (refactoring + docker configuration)
- **Uncertainty**: Low (well-defined requirements)
- **Dependencies**: Low (standalone, no external dependencies)
- **Testing Scope**: Integration (full docker-compose validation)

## Implementation Notes

- Verify catvton service is not used anywhere before removal
- Document all environment variables in .env.example
- Test on clean Docker installation (as if fresh clone)
- Ensure volume mounts preserve node_modules and python packages
- Document startup time target (< 5 minutes)

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Removing catvton breaks other workflows | Search codebase for catvton references before removal |
| Docker Compose version incompatibility | Document required Docker Compose version |
| Performance issues with hot-reload | Test with real-world code changes, optimize polling intervals |

## Owner & Timeline

**Assigned To**: Backend Engineer (Docker expertise)  
**Estimated Duration**: 3-5 days  
**Target Start**: Week 1  
**Blockers**: None

## Definition of Done

- [ ] All 7 stories completed and acceptance criteria met
- [ ] docker-compose.yml runs successfully on fresh machine
- [ ] All team members can start dev environment within 5 minutes
- [ ] Hot-reload verified working
- [ ] Documentation complete and reviewed
- [ ] No critical issues in code review
- [ ] Merged to dev branch

---
id: 008-optimize-layers
unit: 003-container-optimization
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 003-container-optimization
implemented: true
---

# Story: 008-Optimize Layers

## User Story

**As a** developer  
**I want** to optimize Docker image layers  
**So that** builds are faster and images are smaller

## Acceptance Criteria

- [ ] **Given** the Dockerfiles, **When** I review the order, **Then** dependencies are installed before source code copy (layer caching)
- [ ] **Given** the project root, **When** I check .dockerignore, **Then** it excludes node_modules, .git, __pycache__
- [ ] **Given** the Dockerfile instructions, **When** I review RUN commands, **Then** related operations use single RUN command
- [ ] **Given** a code change, **When** I rebuild the image, **Then** build cache is effective (unchanged layers not rebuilt)
- [ ] **Given** the optimized images, **When** I check sizes, **Then** final image size meets targets (frontend < 200MB, backend < 150MB)

## Technical Notes

- Copy package.json and package-lock.json first, then npm ci, then copy source
- For backend: copy requirements.txt first, then pip install, then copy source
- Combine RUN commands: RUN apt-get update && apt-get install -y && rm -rf /var/lib/apt/lists/*
- Use .dockerignore to exclude: node_modules, .git, __pycache__, *.pyc, .env, .venv
- Order matters: less frequently changed files first

## Dependencies

### Requires
- 007-nonroot-user

### Enables
- 010-test-images

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| .dockerignore missing critical pattern | Add pattern to exclude unnecessary files |
| Layer cache invalidated unnecessarily | Review COPY instructions, ensure stable files copied first |
| Multi-stage build not reducing size | Verify only necessary artifacts copied to final stage |

## Out of Scope

- BuildKit advanced features
- Image squashing
- Base image customization

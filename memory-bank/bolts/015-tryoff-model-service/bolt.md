---
id: 015-tryoff-model-service
unit: 001-tryoff-model-service
intent: 004-tryoff-garment-extraction
type: ddd-construction-bolt
status: complete
stories:
  - 003-container-health-monitoring
created: 2026-05-31T00:00:00.000Z
started: 2026-05-31T14:00:00.000Z
completed: "2026-06-01T01:30:03Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-05-31T14:15:00.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-05-31T14:30:00.000Z
    artifact: ddd-02-technical-design.md
  - name: implement
    completed: 2026-05-31T14:35:00.000Z
    artifact: verified-existing-implementation
requires_bolts:
  - 014-tryoff-model-service
enables_bolts:
  - 016-tryoff-job-service
requires_units: []
blocks: false
complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 015-tryoff-model-service

## Overview

Add health check endpoint and container lifecycle management to the TryOff model service. Ensures the job service can detect model readiness and the platform recovers automatically from crashes.

## Objective

Deliver GET /health endpoint with `model_loaded` state, Docker Compose healthcheck config, and auto-restart policy — following the FASHN container management pattern exactly.

## Stories Included

- **003-container-health-monitoring**: Health check endpoint + auto-restart (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Define health state machine (`loading → ready`); `_model_ready` flag lifecycle
- [ ] **2. Technical Design**: GET /health contract; Docker Compose healthcheck config; restart policy
- [ ] **3. Implementation**: Health endpoint + `_model_ready` flag + Docker Compose updates
- [ ] **4. Test**: Verify health returns 503 during load, 200 after ready; simulate crash and confirm restart

## Dependencies

### Requires
- 014-tryoff-model-service (container must be running)

### Enables
- 016-tryoff-job-service (job service checks health before routing)

## Success Criteria

- [ ] GET /health returns 503 while model loads, 200 when ready
- [ ] Container restarts within 30s after simulated crash
- [ ] Docker Compose healthcheck marks container healthy after model is loaded

## Notes

- Port: `TRYOFF_MODEL_PORT` env var (default 8003 to avoid conflict with FASHN on 8002)
- Container name in Docker Compose: `tryoff-model-service`

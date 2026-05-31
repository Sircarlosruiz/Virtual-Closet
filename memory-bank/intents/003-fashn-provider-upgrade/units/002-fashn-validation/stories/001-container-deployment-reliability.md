---
id: 001-container-deployment-reliability
unit: 002-fashn-validation
intent: 003-fashn-provider-upgrade
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 013-fashn-validation
implemented: false
---

# Story: 001-container-deployment-reliability

## User Story

**As a** developer running FASHN locally
**I want** `docker compose up --build fashn` to always serve the latest code
**So that** I can trust that test results reflect the current postprocess.py, not a stale container from a previous session

## Acceptance Criteria

- [ ] **Given** an orphan FASHN process was running on :8002, **When** `docker compose up --build fashn` is run, **Then** either the orphan is killed automatically or the new container successfully binds :8002 (no "port already in use" error)
- [ ] **Given** a rebuild with a code change (e.g., modified `postprocess.py`), **When** the same inputs are sent to /predict with the same seed, **Then** the output MD5 differs from the previous run (confirming new code ran)
- [ ] **Given** a successful rebuild, **When** GET /health is called, **Then** the response includes a `version` or `commit` field that identifies the code revision
- [ ] **Given** the ops procedure, **When** documented, **Then** a kill/restart sequence is written in a runbook file (or Makefile target) that ensures a clean port before compose up

## Technical Notes

- Root cause: an orphan FASHN process (started manually or by a previous compose run) was binding :8002, so `docker compose up --build fashn` started the container but traffic still routed to the orphan.
- Fix options: (a) add `stop_grace_period` + `restart: unless-stopped` to compose service; (b) add a Makefile target `make fashn-restart` that kills :8002 before compose up; (c) configure the compose service to use `network_mode: host` — not recommended.
- Simplest reliable fix: Makefile target `make fashn-restart: $(shell lsof -ti:8002) && kill -9 $$pid; docker compose up --build -d fashn`
- Add a startup log line to `main.py` that prints git commit SHA or `FASHN_BUILD_TAG` env var: `print(f"FASHN container version: {os.environ.get('FASHN_BUILD_TAG', 'dev')}")`
- Determinism check: run `docker compose up --build fashn` → POST /predict with same inputs + `FASHN_SEED=42` → compare MD5 of response bytes before and after the change.

## Dependencies

### Requires
- None (ops fix; independent of code changes)

### Enables
- 002-multi-subject-test-suite — reliable container is prerequisite for valid test results

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| No orphan process on :8002 | Makefile target runs cleanly; compose up proceeds normally |
| Rebuild with no code change | Output MD5 is identical (correct — determinism); version log confirms container rebuilt |
| Docker daemon not running | Compose fails with clear error — not a container reliability issue |

## Out of Scope

- CI/CD pipeline changes
- Production deployment (cloud) — this is local dev reliability only
- Networking changes between FASHN container and Celery worker

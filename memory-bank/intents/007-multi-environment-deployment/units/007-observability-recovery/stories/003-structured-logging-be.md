---
id: 003-structured-logging-be
unit: 007-observability-recovery
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 007-observability-recovery
implemented: true
---

# Story: 003-Structured Logging (Backend)

## User Story

**As a** backend developer  
**I want** structured logging with request IDs in the backend  
**So that** requests can be traced across services

## Acceptance Criteria

- [ ] **Given** an incoming request with an `X-Request-ID` header, **When** the request is received, **Then** the request ID is extracted from the header
- [ ] **Given** an incoming request without an `X-Request-ID` header, **When** the request is received, **Then** a new request ID is generated
- [ ] **Given** a request ID is available, **When** any log entry is emitted, **Then** the request ID is included in the log entry
- [ ] **Given** the logging format is configured, **When** a log entry is written, **Then** the format is JSON (structlog or python-json-logger)
- [ ] **Given** a log entry is emitted, **When** inspected, **Then** it includes: timestamp, level, requestId, method, path, status
- [ ] **Given** a Celery task is triggered from a request, **When** the task executes, **Then** the request ID is propagated to the task's log entries

## Technical Notes

- Use `structlog` with `python-json-logger` for JSON output
- Extract/generate request ID in middleware and store in context (e.g., `contextvars`)
- Propagate request ID to Celery tasks via task headers or kwargs
- Include HTTP method, path, and response status in request-level log entries

## Dependencies

### Requires
- 001-log-aggregation

### Enables
- 004-pod-alerting

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Request ID header is malformed | Generate a new request ID; log a warning about the malformed header |
| Celery task runs without request context | Task generates its own request ID; logs indicate no parent request |
| High-throughput endpoint | Logging does not add measurable latency; JSON serialization is optimized |

## Out of Scope

- Frontend request ID generation (covered in 002-structured-logging-fe)
- Log aggregation infrastructure (covered in 001-log-aggregation)

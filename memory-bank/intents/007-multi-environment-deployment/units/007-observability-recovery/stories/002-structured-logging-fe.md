---
id: 002-structured-logging-fe
unit: 007-observability-recovery
intent: 007-multi-environment-deployment
status: complete
priority: must
created: 2026-06-17T14:45:00.000Z
completed: 2026-07-01T00:00:00Z
assigned_bolt: 007-observability-recovery
implemented: true
---

# Story: 002-Structured Logging (Frontend)

## User Story

**As a** frontend developer  
**I want** structured logging with request IDs in the frontend  
**So that** requests can be traced across services

## Acceptance Criteria

- [ ] **Given** a user initiates a request, **When** the request is created, **Then** a unique request ID is generated
- [ ] **Given** a request ID exists, **When** any log entry is emitted, **Then** the request ID is included in the log entry
- [ ] **Given** the logging format is configured, **When** a log entry is written, **Then** the format is JSON
- [ ] **Given** a log entry is emitted, **When** inspected, **Then** it includes: timestamp, level, requestId, message
- [ ] **Given** a request is sent to the backend, **When** the HTTP call is made, **Then** the request ID is passed via the `X-Request-ID` header

## Technical Notes

- Use `crypto.randomUUID()` or a UUID library for request ID generation
- Wrap `fetch`/`axios` calls to inject `X-Request-ID` header automatically
- Use a lightweight JSON logger (e.g., `pino`, `winston` browser build, or custom formatter)
- Ensure request ID propagation through all async boundaries (promises, event handlers)

## Dependencies

### Requires
- 001-log-aggregation

### Enables
- 004-pod-alerting

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Request ID generation fails | Fallback to a timestamp-based unique identifier |
| Backend does not echo request ID | Frontend logs still contain the original request ID |
| Multiple concurrent requests | Each request gets a unique ID; logs are not interleaved |

## Out of Scope

- Backend request ID handling (covered in 003-structured-logging-be)
- Log aggregation infrastructure (covered in 001-log-aggregation)

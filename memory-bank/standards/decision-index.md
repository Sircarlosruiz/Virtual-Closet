---
last_updated: 2026-05-31T16:30:00Z
total_decisions: 4
---

# Decision Index

This index tracks all Architecture Decision Records (ADRs) created during Construction bolts.
Use this to find relevant prior decisions when working on related features.

## How to Use

**For Agents**: Scan the "Read when" fields below to identify decisions relevant to your current task. Before implementing new features, check if existing ADRs constrain or guide your approach. Load the full ADR for matching entries.

**For Humans**: Browse decisions chronologically or search for keywords. Each entry links to the full ADR with complete context, alternatives considered, and consequences.

---

## Decisions

<!-- Entries are appended below in reverse chronological order (newest first) -->

### ADR-004: Separate Celery Queue for TryOff Jobs
- **Status**: accepted
- **Date**: 2026-05-31
- **Bolt**: 016-tryoff-job-service (002-tryoff-job-service)
- **Path**: `bolts/016-tryoff-job-service/adr-001-separate-celery-queue.md`
- **Summary**: Use a dedicated Celery queue named `tryoff` for all TryOff job processing, separate from the existing `vton` queue, to prevent job starvation and ensure predictable processing times.
- **Read when**: Implementing async job processing, designing Celery task routing, adding new AI-powered features that require background processing, configuring worker pools, troubleshooting job queue performance

### ADR-003: Build-Time Weight Download for FLUX.2-klein Model
- **Status**: accepted
- **Date**: 2026-05-31
- **Bolt**: 014-tryoff-model-service (001-tryoff-model-service)
- **Path**: `bolts/014-tryoff-model-service/adr-003-build-time-weight-download.md`
- **Summary**: The TryOff model service requires FLUX.2-klein-base-9B (~18 GB) and virtual-tryoff-lora weights. Download weights at Docker image build time rather than runtime to ensure deterministic startup and avoid 30+ minute first-start latency.
- **Read when**: Setting up new AI model containers, designing Docker images for GPU services, evaluating weight management strategies, planning CI/CD for ML inference services

### ADR-002: Token Hashing Strategy (bcrypt)
- **Status**: accepted
- **Date**: 2026-05-28
- **Bolt**: 008-customer-portal-service (002-customer-portal-service)
- **Path**: `bolts/008-customer-portal-service/adr-002-token-hashing-strategy.md`
- **Summary**: The customer portal uses invitation and magic-link tokens to authenticate buyers. Hash tokens with bcrypt before storage, never persist plaintext.
- **Read when**: Implementing token-based authentication, storing credentials in database, designing security-critical storage patterns, working with invitation or magic-link flows

### ADR-001: Separate Buyer Authentication Context
- **Status**: accepted
- **Date**: 2026-05-28
- **Bolt**: 008-customer-portal-service (002-customer-portal-service)
- **Path**: `bolts/008-customer-portal-service/adr-001-separate-buyer-auth-context.md`
- **Summary**: The platform serves two distinct user types (mayoristas and buyers) with different access patterns and security requirements. Use completely separate authentication contexts with different cookies, JWT structures, and database tables.
- **Read when**: Designing authentication systems, implementing authorization logic, working with buyer portal or mayorista endpoints, considering role-based access control, evaluating security boundaries between user types

---
bolt: 039-kubernetes-config
created: 2026-06-18T12:00:00Z
status: accepted
superseded_by: null
---

# ADR-036: Redis as Deployment (No PVC) for Staging

## Context

Redis is used in Virtual Closet for three purposes:

1. **Token denylist** (ADR-016, ADR-023, ADR-027): When a user logs out or is force-logged-out, their JWT access token is added to Redis with a TTL equal to the token's remaining lifetime (max 7 days, per `JWT_EXPIRE_DAYS`). On each request, the backend checks if the token is denylisted.
2. **Rate limiting** (via slowapi): Request rate counters stored in Redis with short TTL (~60s windows).
3. **Celery broker**: RabbitMQ is the primary Celery broker; Redis is NOT used as a Celery broker in this stack.

Two deployment options:

1. **Deployment (no PVC)**: Redis runs in-memory only. On pod restart, all denylisted tokens are lost. Any token that was revoked (logged-out) before the pod restart would temporarily be valid again until its natural expiry (max 7 days). Rate limiting counters also reset.

2. **StatefulSet + PVC (10Gi)**: Redis persists the denylist to disk (`appendonly yes`). Pod restarts do not re-validate revoked tokens. Requires an additional PVC on the already-constrained single worker node (80 GB SSD shared with postgres/minio/rabbitmq).

## Decision

Use a **Deployment with no PVC** for staging. Redis runs in-memory only.

Reasoning:
- The token denylist security window is bounded: at worst, a logged-out user can re-use their token for up to 7 days (JWT_EXPIRE_DAYS). For a staging environment, this is acceptable.
- Redis pod restarts are rare (no stateful data to corrupt, no migration needed). On the single-worker k3s cluster, pod restarts happen mainly during deploys or node reboots.
- Eliminates one PVC from the worker's 80 GB SSD. Current PVC allocation: postgres (10 Gi) + minio (20 Gi) + rabbitmq (5 Gi) + backup workspace = ~38 Gi. Adding Redis (even 2 Gi) reduces available headroom.
- `appendonly yes` Redis with a PVC requires fsync on every write — adds latency to token check operations (hot path on every authenticated request).

## Consequences

**Positive:**
- Simpler deployment (Deployment vs StatefulSet — no stable network identity, no PVC lifecycle management)
- No PVC consumption on the already-loaded worker SSD
- Lower write latency on token denylist lookups (pure in-memory)

**Negative / Constraints:**
- On pod restart: all denylisted tokens become valid again for up to 7 days. This is a known security gap acceptable for staging.
- Rate limit counters reset on pod restart — burst traffic during the first 60s after restart is not rate-limited.
- **For production**: evaluate switching to StatefulSet + PVC with `appendonly yes`, or use a managed Redis service (e.g., Hetzner Redis-as-a-Service when available, or Upstash).

**Re-evaluate when**: Planning production deployment, adding compliance requirements around session revocation, scaling to workloads where rate-limit bypass on restart is a business risk.

**Read when**: Implementing logout/force-logout flows, reviewing token security, planning Redis migration to StatefulSet, auditing session management.

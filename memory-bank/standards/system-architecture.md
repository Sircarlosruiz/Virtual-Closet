# System Architecture

## Overview

Layered monorepo architecture: Next.js frontend communicates with a FastAPI backend over REST. Long-running AI inference is decoupled via RabbitMQ + Celery. All binary assets flow through MinIO. The VTON AI provider is abstracted to swap local GPU (dev) for Replicate (prod) without code changes.

---

## Architecture Style

**Backend**: Layered / Domain-Driven within a monolith

```
Client
  → Next.js (SSR/CSR)
      → FastAPI REST API
          → Services (business logic)
              → Repositories (data access)
                  → PostgreSQL (relational data)
          → Celery Workers (async tasks)
              → RabbitMQ (task queue)
              → MinIO (object storage)
              → VTON Provider (IDM-VTON inference)
```

**Key invariant**: each layer only depends on the layer directly below it. Routers do not contain business logic. Services do not import FastAPI. Repositories do not contain business rules.

---

## API Design

**Style**: REST
**Base path**: `/api/` (versioned as `/api/v1/` for explicit versioning going forward)
**Auth**: JWT in HttpOnly cookie — no `Authorization: Bearer` header

**Current router domains**:
- `/api/auth/` — registration, login, logout, token refresh
- `/api/mayoristas/` — wholesaler profile management
- `/api/catalogos/` — catalog CRUD and sharing
- `/api/prendas/` — garment upload and management
- `/api/vton/` — VTON job submission and status polling
- `/api/billing/` — Stripe Checkout, Customer Portal, webhooks

---

## Async Task Architecture

VTON inference is expensive (seconds to minutes). The API never blocks on inference.

```
POST /api/vton/generate
  → validate input → create VTONJob record (status: queued)
  → publish task to RabbitMQ → return { job_id, status: "queued" }

Celery Worker:
  → consume task → update status: processing
  → call VTON Provider (local or Replicate)
  → upload result to MinIO → update status: completed, result_url
  → (optional) notify via webhook or polling

GET /api/vton/jobs/{job_id}
  → return current job status + result_url when ready
```

---

## State Management

**Frontend**: React Server Components for server-side data; `useState`/`useReducer` for local UI state; SWR or React Query for client-side data fetching and polling (VTON job status).

**Backend**: Stateless API — all state in PostgreSQL and MinIO. Celery workers pull jobs from RabbitMQ without shared in-process state.

---

## Caching Strategy

- **MinIO pre-signed URLs**: short-lived (15 min) for secure image access
- **API responses**: no server-side cache layer currently; Next.js `fetch` cache for static data
- **Session**: JWT in cookie (stateless) — no server-side session store

---

## Security Patterns

| Concern | Implementation |
|---------|---------------|
| Authentication | JWT in HttpOnly cookie (not accessible to JS) |
| Authorization | `Depends(get_current_mayorista)` on all protected routes |
| Rate limiting | `slowapi` via `core/limiter.py` (per IP / per user) |
| Input validation | Pydantic schemas on all API inputs |
| CORS | FastAPI CORS middleware, restricted origin list |
| File upload | Type validation + size limits before MinIO write |
| Stripe webhooks | Signature verification (`stripe.Webhook.construct_event`) |
| Secrets | Environment variables via `core/config.py` (pydantic-settings) — never hardcoded |

---

## AI Provider Abstraction

```python
# VTONProvider interface
class VTONProvider:
    async def generate(self, garment_url: str, model_url: str, cloth_type: str) -> str:
        ...

# Implementations
class LocalGPUProvider(VTONProvider): ...   # dev — NVIDIA Titan RTX
class ReplicateProvider(VTONProvider): ...  # prod — IDM-VTON / CatVTON on Replicate
```

Provider is injected at startup based on `VTON_PROVIDER` env var. Adding a new inference backend requires implementing this interface only.

---

## Deployment Architecture

```
Development:
  docker-compose.yml
  ├── postgres:16
  ├── minio
  ├── rabbitmq
  ├── celery_worker (backend image)
  ├── backend (FastAPI, uvicorn)
  └── frontend (Next.js dev server)

Production:
  k3s on Hetzner
  ├── Namespaces per environment
  ├── Persistent volumes for postgres, minio
  ├── Secrets via k3s Secrets (mapped from env)
  └── Ingress for frontend + backend
```

`make docker-infra` — starts all services except frontend and backend (for local dev without Docker for those two).

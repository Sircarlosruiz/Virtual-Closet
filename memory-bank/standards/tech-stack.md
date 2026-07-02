# Tech Stack

## Overview

Full-stack web app with AI try-on capabilities. TypeScript frontend (Next.js 14) + Python backend (FastAPI), communicating via REST. AI inference runs through an abstracted provider pattern supporting local GPU (dev) and Replicate (prod).

## Languages

- **Frontend**: TypeScript (strict mode)
- **Backend**: Python 3.11

TypeScript enforces correctness on the UI layer. Python 3.11 is the ML/AI ecosystem standard and pairs naturally with FastAPI async patterns and SQLAlchemy.

## Framework

- **Frontend**: Next.js 14 (App Router)
- **Backend**: FastAPI (async)

Next.js 14 App Router for SSR, image optimization, and React Server Components. FastAPI for high-throughput async APIs, auto-generated OpenAPI docs, and native Pydantic validation. **Note**: Next.js 14 has breaking changes vs. earlier versions — always read `node_modules/next/dist/docs/` before writing any frontend code.

## Authentication

Custom JWT stored in HttpOnly cookies. No third-party auth service.

- JWT issued by FastAPI (`core/security.py`)
- Cookie set by `api/routers/auth.py`
- Protected routes use `Depends(get_current_mayorista)` from `core/dependencies.py`

## Infrastructure & Deployment

| Environment | Stack |
|-------------|-------|
| Development | Docker Compose — all services (postgres, minio, rabbitmq, celery_worker, frontend, backend) |
| Production | EKS on AWS (us-west-2) — containerized services |

Additional services: RabbitMQ + Celery (async VTON task queue), MinIO (S3-compatible object storage for garment and model images), Stripe (Checkout + Customer Portal).

## AI / ML

| Context | Provider |
|---------|----------|
| Development | `LocalGPUProvider` — NVIDIA Titan RTX, IDM-VTON locally |
| Production | `ReplicateProvider` — IDM-VTON / CatVTON via Replicate API |

Provider abstraction lives in the backend VTON service layer. Cloth type must be specified per inference call.

## Billing

Stripe Checkout + Customer Portal for subscription management.

## Package Manager

- **Frontend**: npm
- **Backend**: pip + virtualenv

## Decision Relationships

FastAPI async was chosen to match the non-blocking nature of VTON inference queuing. Celery + RabbitMQ offload long-running inference jobs so the API stays responsive. MinIO was chosen for S3 compatibility, enabling a straightforward prod migration to AWS S3 if needed.

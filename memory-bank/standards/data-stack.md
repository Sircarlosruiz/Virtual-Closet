# Data Stack

## Overview

PostgreSQL 16 as the primary relational store, accessed via SQLAlchemy async ORM with Alembic migrations. MinIO handles binary object storage (garment images, model photos, generated outputs). Schema changes are always version-controlled through Alembic — never edit production tables manually.

## Database

**PostgreSQL 16** — self-hosted in Docker (dev), containerized in k3s (prod).

Relational model fits the domain well: mayoristas (wholesalers), catálogos, prendas (garments), pedidos (orders), subscriptions. PostgreSQL extensions available when needed (e.g., `uuid-ossp`, `pg_trgm` for search).

## ORM / Database Client

**SQLAlchemy async** (`AsyncSession`) — Python backend only. Frontend communicates exclusively through the FastAPI REST API; it has no direct database access.

Migration tool: **Alembic**

- Generate: `alembic revision --autogenerate -m "description"`
- Apply: `alembic upgrade head`
- Models live in `backend/models/`; always regenerate after any model change.

## Object Storage

**MinIO** (S3-compatible) at `backend/core/` integration.

Used for:
- Uploaded garment photos (flat or mannequin)
- Source model photos
- AI-generated output images
- Catalog assets

Production migration path: swap MinIO endpoint for AWS S3 with no application code changes (same SDK).

## Decision Relationships

AsyncSession was chosen to match FastAPI's async request handling, ensuring database queries don't block the event loop. Alembic is mandatory for schema governance — no DDL outside migrations prevents drift between environments.

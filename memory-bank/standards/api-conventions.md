# API Conventions

## Overview

REST API served by FastAPI. Base path `/api/`, versioned under `/api/v1/`. Authentication via HttpOnly JWT cookie. Consistent JSON response and error shapes across all endpoints.

---

## API Style

**Style**: REST
**Data format**: JSON (request and response)
**Auth**: HttpOnly cookie (`access_token`) — no `Authorization` header

---

## Versioning

**Current**: `/api/{domain}/` (implicit v1)
**Future migration target**: `/api/v1/{domain}/` via `api/v1/` router aggregator (already reserved in project structure)

When adding new endpoints, register them through the v1 aggregator to ease future versioning.

---

## Response Format

### Success responses

FastAPI default — return Pydantic model directly. The schema class defines the shape.

```json
// GET /api/catalogos/{id}
{
  "id": "uuid",
  "name": "Colección Verano 2026",
  "mayorista_id": "uuid",
  "created_at": "2026-05-26T00:00:00Z",
  "items": []
}
```

### List responses

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### Created resources

Return `201 Created` with the created resource body.

---

## Error Response Format

### Simple errors (FastAPI default)

```json
{
  "detail": "Mayorista not found"
}
```

### Domain errors (structured)

```json
{
  "detail": {
    "code": "VTON_PROCESSING_FAILED",
    "message": "The VTON inference failed after 3 retries",
    "context": {
      "job_id": "uuid",
      "provider": "replicate"
    }
  }
}
```

### HTTP Status Codes

| Status | Usage |
|--------|-------|
| `200` | Successful read or update |
| `201` | Resource created |
| `204` | Successful delete (no body) |
| `400` | Validation error (Pydantic auto-handles) |
| `401` | Not authenticated |
| `403` | Authenticated but not authorized |
| `404` | Resource not found |
| `409` | Conflict (e.g., email already registered) |
| `422` | Unprocessable entity (FastAPI Pydantic validation) |
| `429` | Rate limit exceeded |
| `500` | Internal server error (never expose details to client) |

---

## Pagination Strategy

**Style**: page-based (page + page_size)

```
GET /api/catalogos?page=1&page_size=20
```

**Defaults**: `page=1`, `page_size=20`, `max_page_size=100`

All list endpoints must support pagination. Never return unbounded lists.

---

## Request Conventions

- **IDs**: UUID v4 (not sequential integers) — exposed in URLs and responses
- **Timestamps**: ISO 8601 with timezone (`2026-05-26T00:00:00Z`)
- **File uploads**: `multipart/form-data` for garment/model image endpoints
- **Filtering**: query params (`?status=completed&mayorista_id=uuid`)
- **Ordering**: `?order_by=created_at&direction=desc`

---

## VTON-Specific Conventions

VTON jobs follow a submit-and-poll pattern:

```
POST /api/vton/generate        → returns { job_id, status: "queued" }
GET  /api/vton/jobs/{job_id}   → returns { status, result_url? }
```

`cloth_type` is a required field on generate requests (specifies garment category for the model).

---

## Stripe Webhook

```
POST /api/billing/webhook
```

- Raw body must be passed unmodified to `stripe.Webhook.construct_event`
- Verify `Stripe-Signature` header before processing any event
- Return `200 OK` immediately for all valid events; process async if needed

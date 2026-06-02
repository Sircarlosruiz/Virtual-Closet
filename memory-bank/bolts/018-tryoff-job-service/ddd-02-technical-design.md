---
stage: design
bolt: 018-tryoff-job-service
created: 2026-05-31T20:06:00Z
---

## Technical Design: 018-tryoff-job-service

### Architecture Pattern

**Layered Architecture** - Same pattern as bolt 016/017. No new patterns needed.

### Layer Structure

```text
┌─────────────────────────────────────────────────┐
│  Presentation (FastAPI)                         │
│  GET /api/tryoff/jobs?page=1&page_size=20       │
├─────────────────────────────────────────────────┤
│  Application (TryoffJobService)                 │
│  list_jobs() with signed URL generation         │
├─────────────────────────────────────────────────┤
│  Infrastructure (TryoffJobRepo, MinIO)          │
│  SQL: SELECT ... ORDER BY created_at DESC       │
│  LIMIT/OFFSET pagination                        │
└─────────────────────────────────────────────────┘
```

### API Design

- **GET /api/tryoff/jobs**: Query params: page (default 1, min 1), page_size (default 20, max 100)
  - Response: `{ items: TryoffJobHistoryItem[], total: int, page: int, page_size: int }`

### Data Model

- **tryoff_jobs**: Existing table, no changes needed
- **Query**: `SELECT * FROM tryoff_jobs WHERE mayorista_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?`

### Security Design

- **Authentication**: get_current_mayorista dependency (existing)
- **Authorization**: WHERE mayorista_id = ? ensures cross-mayorista isolation

### NFR Implementation

- **Performance**: Indexed query on (mayorista_id, created_at) for fast pagination
- **Scalability**: LIMIT/OFFSET pagination, max page_size 100

---
stage: technical-design
bolt: 042-observability-recovery
created: 2026-06-18T21:15:00Z
---

## Technical Design: Observability & Recovery

---

### Deliverables

| File | Action |
|------|--------|
| `backend/core/middleware.py` | PATCH — append `RequestIDMiddleware` + `RequestIDFilter` + `_request_id_var` |
| `backend/main.py` | PATCH — configure structured log handler; register `RequestIDMiddleware` |
| `frontend/middleware.ts` | CREATE |
| `.github/workflows/health-monitor.yaml` | CREATE |
| `RECOVERY.md` | CREATE |

---

### `backend/core/middleware.py` — additions

Append after the existing `TokenRefreshMiddleware` class:

```python
import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the current request ID, or '-' outside a request context."""
    return _request_id_var.get()


class RequestIDFilter(logging.Filter):
    """Injects the current request ID into every log record."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
```

**Key design points:**

| Decision | Detail |
|----------|--------|
| `ContextVar` for storage | Each async coroutine gets its own context — thread-safe in asyncio; no shared mutable state |
| `token = set(); finally: reset(token)` | Prevents context leak if `call_next` raises an exception |
| Preserve existing header | If `X-Request-ID` is already set (e.g., by nginx or the browser), propagate it rather than generating a new one — allows full end-to-end tracing |
| `logging.Filter` on handler | Added to the `StreamHandler` in `main.py`; runs before formatting, so `%(request_id)s` is available in the format string |
| Default value `"-"` | Outside request context (startup, background tasks), logs show `-` instead of blank |

---

### `backend/main.py` — patches

**Patch 1** — add to imports from `core.middleware`:
```python
from core.middleware import RequestIDFilter, RequestIDMiddleware, TokenRefreshMiddleware
```

**Patch 2** — replace the bare `import logging` block with structured handler setup. Insert immediately after the import block, before `app = FastAPI(...)`:
```python
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
))
_log_handler.addFilter(RequestIDFilter())
logging.root.setLevel(logging.INFO)
logging.root.addHandler(_log_handler)
```

**Patch 3** — register `RequestIDMiddleware` immediately after `app.add_middleware(TokenRefreshMiddleware)`:
```python
app.add_middleware(RequestIDMiddleware)
```

**Middleware execution order** (Starlette processes middleware last-registered-first):
```
Request → RequestIDMiddleware → TokenRefreshMiddleware → CORSMiddleware → route handler
```
`RequestIDMiddleware` runs first — request ID is in context for all subsequent middleware and handler log calls.

---

### `frontend/middleware.ts`

```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const requestId = request.headers.get('x-request-id') ?? crypto.randomUUID();

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-request-id', requestId);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  response.headers.set('x-request-id', requestId);
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon\\.ico).*)'],
};
```

**Notes:**
- `crypto.randomUUID()` is available in the Next.js Edge Runtime (V8 — no Node.js polyfill needed)
- `requestHeaders` propagation makes `x-request-id` visible to `headers()` in Server Components and Route Handlers
- Response header echoes it so browser DevTools show the ID on every response
- Matcher excludes static assets to avoid unnecessary middleware overhead

---

### `.github/workflows/health-monitor.yaml`

```yaml
name: Health Monitor

on:
  schedule:
    - cron: '*/15 * * * *'
  workflow_dispatch:

permissions:
  issues: write

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check backend health
        id: backend
        run: |
          STATUS=$(curl -sf --max-time 10 \
            https://api.staging.virtualcloset.io/health \
            -o /dev/null -w "%{http_code}" || echo "000")
          echo "status=${STATUS}" >> $GITHUB_OUTPUT
          echo "Backend: ${STATUS}"

      - name: Check frontend health
        id: frontend
        run: |
          STATUS=$(curl -sf --max-time 10 \
            https://staging.virtualcloset.io/api/health \
            -o /dev/null -w "%{http_code}" || echo "000")
          echo "status=${STATUS}" >> $GITHUB_OUTPUT
          echo "Frontend: ${STATUS}"

      - name: Alert on failure
        if: steps.backend.outputs.status != '200' || steps.frontend.outputs.status != '200'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TITLE="🚨 Staging health check failed"
          BODY="**Time**: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
          **Backend**: ${{ steps.backend.outputs.status }}
          **Frontend**: ${{ steps.frontend.outputs.status }}
          **Run**: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"

          OPEN=$(gh issue list \
            --repo "${{ github.repository }}" \
            --state open \
            --label staging-incident \
            --json number \
            -q '.[0].number' 2>/dev/null || echo "")

          if [ -n "${OPEN}" ]; then
            gh issue comment "${OPEN}" \
              --repo "${{ github.repository }}" \
              --body "${BODY}"
          else
            gh issue create \
              --repo "${{ github.repository }}" \
              --title "${TITLE}" \
              --body "${BODY}" \
              --label staging-incident
          fi
          exit 1
```

**Deduplication strategy**: label-based (`staging-incident`) rather than title-based — `gh issue list --label` is an exact filter, not a fuzzy search. If an open `staging-incident` issue exists, append a comment. When the incident is resolved, the operator closes the issue manually.

**`exit 1` on failure**: marks the workflow run as failed in the GitHub Actions UI — visible at a glance without reading issue history.

**`permissions: issues: write`**: required for `gh issue create` via `GITHUB_TOKEN`.

---

### `RECOVERY.md` — section outline

| Section | Content |
|---------|---------|
| Pod rollback | `kubectl rollout history`, `kubectl rollout undo`, wait for Ready |
| Pod crash loop | `kubectl describe`, `kubectl logs --previous`, fix config or image, re-deploy |
| Node failure | Force-delete stuck pods, cordon node, drain, investigate |
| Database backup | `kubectl exec postgres-0 -- pg_dump ...` → gzip → store off-cluster |
| Database restore | Scale backend to 0, restore dump, run migrations, scale back |
| Full cluster rebuild | Re-apply manifests in order (from k8s/DEPLOY.md), restore DB, re-run migrations |
| Phase 2 observability | Loki+Promtail, Prometheus, Grafana, Jaeger — scope and rationale |

---

### No new ADRs

All choices are clear defaults:
- `ContextVar` for async request context storage (Python stdlib, no alternatives needed)
- `logging.Filter` on handler (standard Python logging pattern)
- `crypto.randomUUID()` in Edge Runtime (Web API standard)
- GitHub Issues for alerting (no external service needed; `GITHUB_TOKEN` is free)
- Label-based deduplication (more reliable than title-search)

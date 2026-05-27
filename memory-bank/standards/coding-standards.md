# Coding Standards

## Overview

Strict typing on both stacks. Python backend follows PEP 8 + type hints enforced by Ruff. TypeScript frontend uses strict mode with Prettier + ESLint. All AI-generated code must conform to these conventions.

---

## Code Formatting

### Python (Backend)

**Tool**: Ruff (format + lint, Black-compatible)
**Key Settings**:
- Line length: 88 characters (Black default)
- Indentation: 4 spaces
- Quote style: double quotes

**Enforcement**: pre-commit hook + CI

### TypeScript (Frontend)

**Tool**: Prettier
**Key Settings**:
- Single quotes
- Trailing commas: `all`
- Line length: 100 characters
- Semicolons: true
- Tab width: 2 spaces

**Enforcement**: on-save (editor) + pre-commit

---

## Linting

### Python

**Tool**: Ruff
**Strictness**: balanced — type hints required, no unused imports, no bare `except`

**Key Rules**:
- `strict` type hints on all public function signatures
- No unused variables or imports
- No `print()` in production code — use `core/logger.py`
- No bare `except:` — always catch specific exceptions
- Docstrings: Google style for public classes and functions

**Type checking**: mypy (strict) on services and repositories

### TypeScript

**Tool**: ESLint with `@typescript-eslint/recommended`
**Strictness**: strict

**Key Rules**:
- `strict: true` in tsconfig — no implicit any
- No `any` type — use `unknown` and narrow
- Unused variables: error
- Explicit return types on exported functions
- No `console.log` in production code

---

## Naming Conventions

### Python (Backend)

| Element | Convention | Example |
|---------|------------|---------|
| Variables | snake_case | `user_name`, `is_active` |
| Functions | snake_case | `get_mayorista_by_id` |
| Classes | PascalCase | `MayoristaService`, `AuthRepository` |
| Constants | UPPER_SNAKE | `MAX_UPLOAD_SIZE`, `JWT_ALGORITHM` |
| Modules | snake_case | `mayorista_repo.py`, `auth_service.py` |
| Private members | Leading underscore | `_hash_password` |
| Routers | `*_router` variable name | `auth_router = APIRouter()` |
| Repositories | `*_repo.py` files, `*Repo` classes | `mayorista_repo.py` |
| Services | `*_service.py` files, `*Service` classes | `auth_service.py` |

### TypeScript (Frontend)

| Element | Convention | Example |
|---------|------------|---------|
| Variables | camelCase | `userName`, `isActive` |
| Functions | camelCase | `getUserById`, `handleSubmit` |
| Classes | PascalCase | `UserService` |
| Interfaces / Types | PascalCase | `Mayorista`, `ApiResponse` |
| Constants | UPPER_SNAKE or camelCase | `MAX_RETRIES`, `apiBaseUrl` |
| React components | PascalCase | `CatalogCard`, `UploadButton` |
| React hooks | camelCase with `use` prefix | `useAuth`, `useCatalog` |
| Files (components) | PascalCase | `CatalogCard.tsx` |
| Files (utilities/hooks) | kebab-case | `use-auth.ts`, `date-utils.ts` |
| Files (pages/routes) | Next.js App Router conventions | `page.tsx`, `layout.tsx`, `loading.tsx` |

---

## File Organization

### Backend

**Pattern**: Domain-driven layers — each domain traverses all layers top-to-bottom.

```text
backend/
├── main.py                    # App entry, middleware, router registration
├── api/
│   ├── routers/               # HTTP endpoints (one file per domain)
│   ├── schemas/               # Pydantic DTOs (request/response per domain)
│   └── v1/                    # Versioned router aggregator
├── services/                  # Business logic (no FastAPI dependency)
├── repositories/              # Data access (AsyncSession queries)
├── models/                    # SQLAlchemy ORM entities
├── core/                      # Cross-cutting: config, db, security, deps, logger
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── dependencies.py
│   ├── middleware.py
│   ├── limiter.py
│   └── logger.py
└── tests/                     # pytest integration/E2E tests
```

**Adding a new domain** (e.g., `catalogo`):
1. `models/catalogo.py` → `repositories/catalogo_repo.py` → `services/catalogo_service.py`
2. `api/schemas/catalogo.py` → `api/routers/catalogo.py`
3. Register router in `main.py`
4. Generate Alembic migration

### Frontend

**Pattern**: Next.js 14 App Router conventions.

```text
frontend/
├── app/                       # App Router: pages, layouts, loading states
│   ├── (auth)/                # Route groups (no URL segment)
│   ├── dashboard/
│   └── layout.tsx
├── components/                # Shared UI components
│   ├── ui/                    # shadcn/ui base components
│   └── {feature}/             # Feature-specific components
├── hooks/                     # Custom React hooks
├── lib/                       # Utilities, API clients
└── types/                     # Shared TypeScript types
```

**Conventions**:
- Tests: co-located `.test.ts` or `__tests__/` within feature folder
- Types: co-located with the feature or in `types/` for shared types
- No barrel re-exports (`index.ts`) unless the folder is a true public API

---

## Testing Strategy

### Backend

**Framework**: pytest + httpx (async test client)
**Coverage Target**: critical paths covered — auth flows, VTON service, billing hooks

| Type | Tool | When to Use |
|------|------|-------------|
| Integration | pytest + httpx | API endpoints, auth, rate limits |
| Unit | pytest | Services, repositories in isolation |
| E2E | Playwright | Full user flows (optional) |

**Conventions**:
- Test naming: `test_should_{behavior}_when_{condition}`
- Structure: Arrange → Act → Assert
- Mock strategy: mock at boundaries (external APIs, MinIO, Replicate); use real PostgreSQL for data tests
- Test DB: separate test database, reset per test session

### Frontend

**Framework**: Playwright for E2E
**Coverage Target**: critical user journeys (upload garment → generate → view catalog)

**Conventions**:
- Component tests: Testing Library (React)
- E2E: Playwright against local dev server
- No snapshot tests unless specifically needed

---

## Error Handling

### Backend

**Pattern**: Domain exceptions in services → translated to `HTTPException` in routers

```python
# services/ — raise domain exceptions
raise MayoristaNotFoundError(f"Mayorista {id} not found")

# api/routers/ — translate to HTTP
except MayoristaNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
```

**Custom Errors**: Yes — domain error classes in `services/` (e.g., `VTONProcessingError`, `SubscriptionExpiredError`)
**Async errors**: always `try/except` with specific exception types — no bare `except`
**API Error format**: FastAPI default `{"detail": "message"}` for simple errors; structured `{"detail": {"code": "...", "message": "...", "context": {}}}` for domain errors

### Frontend

**Pattern**: `try/catch` on API calls; React Error Boundaries for UI
**API errors**: propagated from fetch/axios response, displayed via toast or inline error state
**User-facing errors**: human-readable messages only — no stack traces in UI

---

## Logging

### Backend

**Tool**: Centralized `core/logger.py` (structlog or standard logging with JSON formatter)
**Format**: structured JSON in production, human-readable in development

| Level | Usage |
|-------|-------|
| `error` | Unhandled exceptions, inference failures, DB errors |
| `warn` | Retries, degraded state, unexpected but handled conditions |
| `info` | Auth events, VTON job lifecycle (created, queued, completed) |
| `debug` | Request/response bodies, query details (dev only) |

**Always log**:
- API request: method, path, status, duration
- Auth events: login, logout, token refresh, failed attempts
- VTON job events: created, queued, started, completed, failed
- Billing events: subscription created, payment failed, plan changed

**Never log**:
- Passwords, tokens, API keys, JWT contents
- Full request bodies containing PII
- MinIO pre-signed URLs (contain embedded credentials)

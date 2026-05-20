# Backend — Virtual Closet API

Guía de estructura y convenciones para agentes que implementan el backend (subagente **Backend Engineer**). Stack: FastAPI, PostgreSQL, SQLAlchemy async, Alembic, RabbitMQ (futuro).

## Flujo de capas

Las peticiones HTTP siguen este orden. Cada capa solo conoce la inmediatamente inferior:

```
Cliente HTTP
    → api/routers        (entrada HTTP: rutas, status codes, cookies)
    → services/          (reglas de negocio y orquestación)
    → repositories/      (acceso a datos: queries, commits)
    → models/            (entidades SQLAlchemy / tablas PostgreSQL)
```

`api/schemas` valida y serializa el contrato de la API (Pydantic). `core/` provee configuración, BD, seguridad y dependencias compartidas.

## Estructura de carpetas

```
backend/
├── main.py                 # Punto de entrada: app FastAPI, middlewares, routers
├── alembic/                # Migraciones de esquema PostgreSQL
│   ├── env.py
│   └── versions/           # Scripts de migración (Alembic)
├── api/                    # Capa HTTP / contrato REST
│   ├── routers/            # Endpoints FastAPI (APIRouter por dominio)
│   ├── schemas/            # Modelos Pydantic: request/response, validación
│   └── v1/                 # Agrupación versionada (reservado para /api/v1)
├── controllers/            # Orquestación HTTP alternativa (reservado; vacío hoy)
├── services/               # Lógica de negocio (sin dependencia de FastAPI)
├── repositories/           # Persistencia: consultas y transacciones SQLAlchemy
├── models/                 # Modelos de datos ORM (tablas, relaciones, índices)
├── core/                   # Infraestructura transversal de la aplicación
│   ├── config.py           # Settings (variables de entorno, pydantic-settings)
│   ├── database.py         # Engine async, sesión, get_db
│   ├── security.py         # JWT, hash de contraseñas
│   ├── dependencies.py     # Depends compartidos (ej. usuario autenticado)
│   ├── middleware.py       # Middlewares Starlette/FastAPI
│   ├── limiter.py          # Rate limiting (slowapi)
│   └── logger.py           # Logging centralizado
└── tests/                  # Pruebas pytest (API, auth, rate limit, etc.)
```

### Descripción por carpeta

| Carpeta | Responsabilidad | Qué va aquí | Qué no va aquí |
|---------|-----------------|-------------|----------------|
| **`models/`** | Modelo de datos (ORM) | Clases SQLAlchemy, `Base`, columnas, índices, relaciones | Lógica de negocio, queries complejas en routers |
| **`repositories/`** | Acceso a datos | `select`, `create`, `update`, `delete`; uso de `AsyncSession` | Reglas de negocio, validación HTTP, envío de emails |
| **`services/`** | Lógica de negocio | Casos de uso: registro, login, reglas de plan/trial; excepciones de dominio | Rutas FastAPI, modelos Pydantic de API |
| **`api/routers/`** | Controladores HTTP | `@router.post`, códigos HTTP, cookies, llamadas a `*Service` | SQL directo, reglas de negocio extensas |
| **`api/schemas/`** | Contrato API (DTOs) | `RegisterRequest`, `LoginResponse`, validadores Pydantic | Entidades de BD, queries |
| **`api/v1/`** | Versionado API | Router agregador `/api/v1` cuando se migre a versionado explícito | Lógica de negocio |
| **`controllers/`** | Capa intermedia HTTP (opcional) | Coordinación entre varios servicios por request, si la ruta crece mucho | Persistencia, modelos ORM |
| **`core/`** | Configuración e infra | Settings, BD, JWT, middleware, `Depends`, rate limit | Endpoints, reglas de producto |
| **`alembic/`** | Migraciones BD | Cambios de esquema versionados (`alembic revision`, `upgrade`) | Código de runtime de la API |
| **`tests/`** | Pruebas automatizadas | Tests de integración/E2E contra la app y fixtures | Código de producción |

## Convenciones al añadir código

1. **Nuevo dominio** (ej. `catalogo`): `models/catalogo.py` → `repositories/catalogo_repo.py` → `services/catalogo_service.py` → `api/schemas/catalogo.py` → `api/routers/catalogo.py` → registrar router en `main.py`.
2. **Nombres**: un router por archivo en `api/routers/`; un repositorio por agregado (`*_repo.py`); un servicio por caso de uso principal (`*_service.py`).
3. **Dependencias**: inyectar `AsyncSession` con `Depends(get_db)` en routers; pasar el repo al servicio en el constructor (`AuthService(repo)`).
4. **Errores de negocio**: excepciones en `services/`; el router las traduce a `HTTPException` y status codes.
5. **Autenticación**: `core/dependencies.py` (`get_current_mayorista`) para rutas protegidas.
6. **Migraciones**: tras cambiar `models/`, generar revisión en `alembic/versions/`; no editar tablas solo a mano en producción.

## Ejemplo actual (auth)

| Capa | Archivo |
|------|---------|
| Modelo | `models/mayorista.py` |
| Repositorio | `repositories/mayorista_repo.py` |
| Servicio | `services/auth_service.py`, `services/email_service.py` |
| Schemas | `api/schemas/auth.py` |
| Router | `api/routers/auth.py` (`/api/auth/*`) |

## Rol Backend Engineer

Subagente: `.agents/subagents/engineering/backend_engineer.yaml`  
Índice de subagentes: `.agents/AGENTS.md` (sección Backend Engineer y guías por stack)

- APIs robustas, async y seguras (FastAPI + PostgreSQL).
- Diseño de esquemas: `postgresql-table-design`, `postgresql-optimization`, `postgresql-code-review`.
- Estructura de proyecto: `fastapi-templates`.
- ORM y migraciones: SQLAlchemy + Alembic.
- Mensajería async (futuro): `rabbitmq-development`.

## Comandos útiles

Desde la raíz del monorepo (ver `Makefile`):

- Levantar API en desarrollo: `make backend-dev` (o equivalente documentado en el Makefile).
- Tests: `pytest` dentro de `backend/` con el venv activado.
- Migraciones: `alembic upgrade head` / `alembic revision --autogenerate -m "descripción"`.

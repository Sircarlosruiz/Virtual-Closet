# Virtual Closet — Contexto del proyecto

> Fuente de verdad para agentes (Planner, Executor, Auditor, Orquestador y subagentes BMM).
> Índice de roles: [`AGENTS.md`](AGENTS.md)

## Resumen

**Virtual Closet (NikaCommerce)** es una plataforma SaaS B2B para mayoristas de ropa. Transforma fotos planas o en maniquí en catálogos visuales con IA (IDM-VTON) sobre modelos reales en menos de 5 minutos.

## Stack

| Capa | Tecnología |
|------|------------|
| Frontend | Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI (Python 3.11), SQLAlchemy async, Alembic |
| Base de datos | PostgreSQL 16 |
| Colas | RabbitMQ + Celery |
| Almacenamiento | MinIO (S3-compatible) |
| IA (dev) | LocalGPUProvider (NVIDIA Titan RTX) |
| IA (prod) | ReplicateProvider (IDM-VTON) |
| Auth | JWT en cookie HttpOnly |
| Billing | Stripe Checkout + Customer Portal |
| Despliegue | Docker Compose (dev), k3s en Hetzner (prod) |
| Accesibilidad | WCAG AA |

## Estructura del monorepo

```
virtual_closet/
├── frontend/          # Next.js
├── backend/           # FastAPI
├── .agents/           # Agentes, skills, workflows, artefactos
│   ├── workflows/     # Pipeline OpenCode (orquestador, planner, executor, auditor)
│   ├── skills/
│   ├── subagents/
│   ├── reports/       # Reportes de ejecución y auditoría
│   ├── planning-artifacts/
│   └── implementation-artifacts/
├── _framework/        # Configuración BMM
└── Makefile
```

## Guías por stack

| Stack | Archivo |
|-------|---------|
| Backend | [`backend/AGENTS.md`](../backend/AGENTS.md) |
| Frontend | [`frontend/AGENTS.md`](../frontend/AGENTS.md) |
| Subagentes | [`.agents/AGENTS.md`](AGENTS.md) |

## Comandos útiles

| Comando | Descripción |
|---------|-------------|
| `make docker-infra` | Infra Docker (postgres, minio, rabbitmq, celery) sin frontend/backend |
| `make backend-dev` | API en desarrollo (ver Makefile) |
| `pytest` (en `backend/`) | Tests backend |

## Convenciones

- **Idioma:** español en comunicación y documentación de agentes.
- **PRs:** flujo `pr-flow`; target por defecto `dev`.
- **Backend:** capas `routers → services → repositories → models` (ver `backend/AGENTS.md`).
- **Frontend:** seguir guías en `node_modules/next/dist/docs/` (Next.js con breaking changes vs. versiones anteriores).
- **Migraciones:** Alembic tras cambios en `backend/models/`; no editar esquema a mano en producción.

## Artefactos de planificación

| Ruta | Uso |
|------|-----|
| `.agents/planning-artifacts/` | PRD, arquitectura, UX, épicas |
| `.agents/implementation-artifacts/` | Sprint status, historias |
| `.agents/reports/` | Planes ejecutados y auditorías (pipeline OpenCode) |

## Workflows multi-agente (OpenCode / Cursor)

| Workflow | Archivo |
|----------|---------|
| Orquestador | `.agents/workflows/orchestrator.md` |
| Planificación | `.agents/workflows/planner.md` |
| Ejecución | `.agents/workflows/executor.md` |
| Auditoría | `.agents/workflows/auditor.md` |

Adaptadores: `.opencode/agents/*-agent.md` (symlinks al contenido canónico).

## Configuración BMM

Ver `_framework/bmm/config.yaml` — `project_key: VC`, `communication_language: es`.

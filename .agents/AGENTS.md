# Directorio de Subagentes — Virtual Closet

## Descripción del Proyecto

**Virtual Closet (NikaCommerce)** es una plataforma SaaS B2B diseñada para mayoristas de ropa. Permite transformar fotos planas o en maniquí de prendas de vestir en catálogos visuales profesionales generados por Inteligencia Artificial (IDM-VTON) sobre modelos reales en menos de 5 minutos.

El objetivo es eliminar los altos costos de sesiones fotográficas y permitir a los mayoristas compartir catálogos digitales interactivos con sus revendedores a través de enlaces simples (ej. WhatsApp), aumentando la confianza visual y, consecuentemente, el volumen de pedidos.

**Stack tecnológico principal:** Next.js 14, FastAPI (Python), PostgreSQL 16, RabbitMQ, Celery, MinIO, Docker y k3s.

## Guías de implementación por stack

Antes de implementar o revisar código en un stack, cargar la guía correspondiente:

| Stack | Guía |
|-------|------|
| Backend (FastAPI) | [`backend/AGENTS.md`](../backend/AGENTS.md) — capas, carpetas y convenciones |
| Frontend (Next.js) | [`frontend/AGENTS.md`](../frontend/AGENTS.md) — reglas del agente Next.js |

## Comandos útiles

| Comando | Descripción |
|---------|-------------|
| `make docker-infra` | Levanta todos los servicios Docker excepto frontend y backend (postgres, minio, rabbitmq, celery_worker) |

---

## Contexto y workflows

| Recurso | Ruta |
|---------|------|
| Contexto del proyecto (stack, convenciones) | [`.agents/PROJECT.md`](PROJECT.md) |
| Pipeline automático (Planner → Executor → Auditor) | [`.agents/workflows/`](workflows/) |
| Reportes de ejecución | `.agents/reports/` |
| Adaptadores OpenCode | `.opencode/agents/*-agent.md` → symlinks a `workflows/` |

---

## Catálogo de skills (`.agents/skills/`)

Skills instaladas en el proyecto, agrupadas por dominio. Cada subagente carga solo las skills asignadas en su YAML.

| Dominio | Skills |
|---------|--------|
| **Framework / agentes** | `agent-architect`, `agent-dev`, `agent-pm`, `help` |
| **Producto y planificación** | `product-brief`, `sprint-planning`, `create-story`, `create-architecture`, `create-ux-design`, `dev-story` |
| **Entrega y Git** | `quick-dev`, `code-review`, `git-sync`, `pr-flow` |
| **Frontend** | `frontend-design`, `ui-ux-pro-max`, `shadcn`, `tailwind-design-system`, `next-best-practices`, `typescript-advanced-types` |
| **Backend** | `fastapi-templates`, `postgresql-table-design`, `postgresql-optimization`, `postgresql-code-review`, `rabbitmq-development` |
| **ML / IA** | `machine-learning-engineer`, `machine-learning`, `transformers-huggingface`, `langchain-fundamentals`, `langchain-architecture`, `langchain-rag` |
| **DevOps / infra** | `docker-expert`, `multi-stage-dockerfile`, `minio`, `kubernetes-specialist` |
| **Calidad** | `test-atdd` |
| **Documentación** | `distillator` |

> **Nota:** `pr-flow` vive en la carpeta `pr-flow/` (el skill interno se identifica como `lvz-pr-flow`). Algunas skills de framework (`create-story`, `dev-story`, etc.) usan `workflow.md` en lugar de `SKILL.md`.

---

## Estructura de subagentes

La arquitectura se divide en **cuatro dominios** para optimizar la colaboración técnica y el enfoque de las herramientas AI.

```
.agents/subagents/
├── leadership/
│   ├── product_lead.yaml
│   ├── system_architect.yaml
│   └── lead_developer.yaml
├── engineering/
│   ├── frontend_engineer.yaml
│   ├── backend_engineer.yaml
│   ├── ml_engineer.yaml
│   └── devops_engineer.yaml
└── quality/
    ├── qa_engineer.yaml
    └── ux_researcher.yaml
```

---

## 1. Dominio de Liderazgo (Leadership)

Responsables de la orquestación, visión del producto, arquitectura técnica y gestión de la entrega.

### Product Lead (John)

* **Ruta:** `.agents/subagents/leadership/product_lead.yaml`
* **Enfoque:** El "Por qué" y el "Qué". PRDs, product briefs, backlog y planificación de sprints.
* **Skills:** `product-brief`, `agent-pm`, `help`, `sprint-planning`, `create-story`

### System Architect (Winston)

* **Ruta:** `.agents/subagents/leadership/system_architect.yaml`
* **Enfoque:** Escala, consistencia y decisiones técnicas de largo plazo.
* **Skills:** `agent-architect`, `distillator`, `help`, `create-architecture`

### Lead Developer (Amelia)

* **Ruta:** `.agents/subagents/leadership/lead_developer.yaml`
* **Enfoque:** El "Cómo" y terminar. TDD, historias, revisión de código y flujo Git/PR.
* **Skills:** `agent-dev`, `quick-dev`, `code-review`, `git-sync`, `pr-flow`, `dev-story`, `create-story`
* **Guías de stack:** [`backend/AGENTS.md`](../backend/AGENTS.md), [`frontend/AGENTS.md`](../frontend/AGENTS.md)

---

## 2. Dominio de Ingeniería (Engineering)

Especialistas técnicos responsables de la implementación a través del stack.

### Frontend Engineer

* **Ruta:** `.agents/subagents/engineering/frontend_engineer.yaml`
* **Enfoque:** React/Next.js 14, TypeScript, Tailwind, shadcn/ui y UI de alto rendimiento.
* **Skills:** `frontend-design`, `ui-ux-pro-max`, `shadcn`, `tailwind-design-system`, `next-best-practices`, `typescript-advanced-types`

### Backend Engineer

* **Ruta:** `.agents/subagents/engineering/backend_engineer.yaml`
* **Enfoque:** FastAPI, PostgreSQL, RabbitMQ/Celery y APIs asíncronas.
* **Guía de estructura:** [`backend/AGENTS.md`](../backend/AGENTS.md)
* **Skills:** `fastapi-templates`, `postgresql-table-design`, `postgresql-optimization`, `postgresql-code-review`, `rabbitmq-development`

### ML Engineer

* **Ruta:** `.agents/subagents/engineering/ml_engineer.yaml`
* **Enfoque:** Inferencia IDM-VTON, Hugging Face, despliegue de modelos y orquestación LLM (LangChain).
* **Skills:** `machine-learning-engineer`, `machine-learning`, `transformers-huggingface`, `langchain-fundamentals`, `langchain-architecture`, `langchain-rag`

### DevOps Engineer

* **Ruta:** `.agents/subagents/engineering/devops_engineer.yaml`
* **Enfoque:** Docker, MinIO, k3s y pipelines de despliegue.
* **Skills:** `docker-expert`, `multi-stage-dockerfile`, `minio`, `kubernetes-specialist`

---

## 3. Dominio de Calidad (Quality)

Responsables de estándares de código, pruebas y experiencia de usuario.

### QA Engineer

* **Ruta:** `.agents/subagents/quality/qa_engineer.yaml`
* **Enfoque:** ATDD, pruebas automatizadas (Playwright) y revisión adversarial de código.
* **Skills:** `code-review`, `test-atdd`

### UX Researcher

* **Ruta:** `.agents/subagents/quality/ux_researcher.yaml`
* **Enfoque:** UX, diseño de interacción y validación de hipótesis de producto.
* **Skills:** `ui-ux-pro-max`, `create-ux-design`

---

## Matriz de delegación rápida

| Tarea | Subagente recomendado |
|-------|------------------------|
| PRD, épicas, sprint status | Product Lead |
| Arquitectura, ADRs, integraciones | System Architect |
| Implementar historia, PR, dev-story | Lead Developer |
| UI Next.js, componentes | Frontend Engineer |
| API FastAPI, DB, colas | Backend Engineer |
| IDM-VTON, modelos HF, LangChain | ML Engineer |
| Docker, k3s, MinIO | DevOps Engineer |
| Tests E2E / ATDD, code review | QA Engineer |
| Flujos UX, wireframes | UX Researcher |

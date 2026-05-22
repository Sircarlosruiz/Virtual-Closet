# Directorio de Subagentes — Virtual Closet

## Descripción del Proyecto

**Virtual Closet (NikaCommerce)** es una plataforma SaaS B2B diseñada para mayoristas de ropa. Permite transformar fotos planas o en maniquí de prendas de vestir en catálogos visuales profesionales generados por Inteligencia Artificial (IDM-VTON) sobre modelos reales en menos de 5 minutos. 

El objetivo es eliminar los altos costos de sesiones fotográficas y permitir a los mayoristas compartir catálogos digitales interactivos con sus revendedores a través de enlaces simples (ej. WhatsApp), aumentando la confianza visual y, consecuentemente, el volumen de pedidos.

**Stack Tecnológico Principal:** Next.js 14, FastAPI (Python), PostgreSQL 16, RabbitMQ, Celery, MinIO, Docker y k3s.

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

Este documento describe la estructura de subagentes especializados para el proyecto Virtual Closet. La arquitectura se divide en tres dominios principales para optimizar la colaboración técnica y el enfoque de las herramientas AI.

## 1. Dominio de Liderazgo (Leadership)
Responsables de la orquestación, visión del producto, arquitectura técnica y gestión de la entrega.

### 👑 Product Lead (John)
* **Ruta:** `.agents/subagents/leadership/product_lead.yaml`
* **Enfoque:** El "Por qué" y el "Qué". Experto en creación de PRDs, product briefs y refinamiento del backlog basado en valor.
* **Habilidades:** `product-brief`, `agent-pm`, `help`, `brainstorming`

### 🏗️ System Architect (Winston)
* **Ruta:** `.agents/subagents/leadership/system_architect.yaml`
* **Enfoque:** La "Escala" y la "Consistencia". Experto en decisiones técnicas, diseño de sistemas y viabilidad a largo plazo.
* **Habilidades:** `agent-architect`, `distillator`, `help`

### 🚀 Lead Developer (Amelia)
* **Ruta:** `.agents/subagents/leadership/lead_developer.yaml`
* **Enfoque:** El "Cómo" y en "Terminar". Experto en TDD, implementación de historias y calidad automatizada.
* **Habilidades:** `agent-dev`, `quick-dev`, `code-review`, `git-sync`, `lvz-pr-flow`
* **Guías de stack:** [`backend/AGENTS.md`](../backend/AGENTS.md), [`frontend/AGENTS.md`](../frontend/AGENTS.md)

---

## 2. Dominio de Ingeniería (Engineering)
Especialistas técnicos responsables de la implementación a través del stack tecnológico.

### 🎨 Frontend Engineer
* **Ruta:** `.agents/subagents/engineering/frontend_engineer.yaml`
* **Enfoque:** Especialista en el ecosistema de React/Next.js, TypeScript, Tailwind CSS, shadcn/ui y construcción de UI de alto rendimiento.
* **Habilidades:** `frontend-design`, `ui-ux-pro-max`, `shadcn`, `tailwind-design-system`, `next-best-practices`, `vercel-react-best-practices`, `typescript-advanced-types`

### ⚙️ Backend Engineer
* **Ruta:** `.agents/subagents/engineering/backend_engineer.yaml`
* **Enfoque:** Especialista en FastAPI, PostgreSQL, RabbitMQ y arquitectura de microservicios asíncronos.
* **Guía de estructura:** [`backend/AGENTS.md`](../backend/AGENTS.md) — capas (`models` → `repositories` → `services` → `api/routers`), convenciones y comandos.
* **Habilidades:** `fastapi-templates`, `postgresql-table-design`, `postgresql-optimization`, `postgresql-code-review`, `rabbitmq-development`, `sqlalchemy-orm`, `sqlalchemy-alembic-expert-best-practices-code-review`

### ☁️ DevOps Engineer
* **Ruta:** `.agents/subagents/engineering/devops_engineer.yaml`
* **Enfoque:** Especialista en infraestructura, contenedores Docker y almacenamiento de objetos (MinIO).
* **Habilidades:** `docker-expert`, `minio`

---

## 3. Dominio de Calidad (Quality)
Responsables de asegurar los estándares de código, pruebas y la experiencia de usuario final.

### 🛡️ QA Engineer
* **Ruta:** `.agents/subagents/quality/qa_engineer.yaml`
* **Enfoque:** Especialista en aseguramiento de calidad, pruebas automatizadas y auditoría de código.
* **Habilidades:** `code-review`

### 🔍 UX Researcher
* **Ruta:** `.agents/subagents/quality/ux_researcher.yaml`
* **Enfoque:** Especialista en experiencia de usuario, diseño de interacción y validación de hipótesis de producto.
* **Habilidades:** `ui-ux-pro-max`, `brainstorming`
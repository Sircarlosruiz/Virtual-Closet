---
unit: 004-openai-generation-ui
intent: 008-openai-image-generation
phase: inception
status: draft
unit_type: frontend
default_bolt_type: simple-construction-bolt
created: 2026-09-17T01:23:26Z
updated: 2026-09-17T01:23:26Z
---

# Unit Brief: OpenAI Generation UI

## Purpose

Dar al staff una experiencia coherente para administrar plantillas, iniciar los cuatro modos, revisar resultados y seleccionar publicaciones desde Virtual Closet; BFashion ofrece el punto de entrada contextual al producto.

## Scope

### In Scope
- Formularios de los cuatro modos y selección de proveedor/plantilla.
- Estado asíncrono, comparación, edición de SKU y revisión manual.
- Galería de selección y estados de sincronización.

### Out of Scope
- Autorización de servidor, secretos y reglas de tenant.
- Persistencia de dominio e inferencia.

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1..FR-12 | Presentación y consumo de APIs de requisitos asignados a unidades backend | Must |

## Dependencies

- **Depends on**: 001, 002, 003.
- **External**: Next.js/shadcn existing UI; BFashion React/Vite admin entry.

## Story Summary

- **Total Stories**: 3
- **Must Have**: 3
- **Should Have**: 0
- **Could Have**: 0

| Story ID | Title | Priority | Status |
|---|---|---|---|
| 001-generation-form | Generation form | Must | Planned |
| 002-generation-review | Generation review | Must | Planned |
| 003-product-integration-ui | Product integration UI | Must | Planned |

## Success Criteria

- [ ] El staff distingue proveedor, modo, plantilla, borrador, resultado y publicado.
- [ ] Los mayoristas no ven controles de generación.
- [ ] La revisión permite seleccionar imágenes sin publicar automáticamente.
- [ ] Los errores de OpenAI, storage y sync son accionables y accesibles.

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 049-openai-generation-ui | Simple | 004-001, 004-002, 004-003 | Staff workflows and review |

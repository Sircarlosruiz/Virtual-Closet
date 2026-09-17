---
unit: 001-image-generation-service
intent: 008-openai-image-generation
phase: inception
status: draft
created: 2026-09-17T01:23:26Z
updated: 2026-09-17T01:23:26Z
---

# Unit Brief: Image Generation Service

## Purpose

Coordinar trabajos de generación de imágenes con OpenAI o el proveedor VTON actual, con ejecución asíncrona, autorización de staff, persistencia, reintentos e historial.

## Scope

### In Scope
- Modos model try-on, texto, edición y extracción.
- Selección de proveedor por trabajo, API key de plataforma y límites de consumo.
- Estados, idempotencia, retry policy, resultados y auditoría.

### Out of Scope
- Definición/versionado de plantillas y overlays deterministas.
- Publicación en productos BFashion o interfaces de usuario.

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Operación exclusiva del staff | Must |
| FR-2 | Credencial y selección del proveedor | Must |
| FR-5 | Prendas sobre modelos | Must |
| FR-6 | Generación desde texto | Must |
| FR-7 | Edición de imágenes | Must |
| FR-8 | Extracción de prendas | Must |
| FR-9 | Trabajos asíncronos e historial | Must |
| FR-13 | Registro de consumo | Must |

## Domain Concepts

| Entity | Description |
|--------|-------------|
| GenerationJob | Solicitud, modo, proveedor, inputs, estado e idempotency key |
| GenerationResult | Imagen base/resultante, estado de revisión y metadata |
| ProviderInvocation | Llamada OpenAI/VTON, modelo, retries, uso y error |
| StaffGenerationPolicy | Autorización y límites de ejecución |

## Dependencies

- **Depends on**: Auth, media/storage, RabbitMQ/Celery.
- **Depended by**: 002-template-composition-service, 003-product-image-integration, 004-openai-generation-ui.
- **External**: OpenAI Image API (high), MinIO (medium), RabbitMQ/Celery (medium).

## Story Summary

- **Total Stories**: 5
- **Must Have**: 5
- **Should Have**: 0
- **Could Have**: 0

| Story ID | Title | Priority | Status |
|---|---|---|---|
| 001-staff-provider-selection | Staff provider selection | Must | Planned |
| 002-staff-generation-jobs | Staff generation jobs | Must | Planned |
| 003-provider-invocation-history | Provider invocation history | Must | Planned |
| 004-retry-idempotency-limits | Retry, idempotency and limits | Must | Planned |
| 005-usage-recording | Usage recording | Must | Planned |

## Success Criteria

- [ ] Los cuatro modos generan trabajos y resultados persistidos.
- [ ] OpenAI no se expone al cliente y VTON continúa seleccionable para try-on.
- [ ] Permisos, idempotencia, retries e historial pasan pruebas de integración.
- [ ] Se registra consumo informado o desconocido sin inventar cero.

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 043-image-generation-service | DDD | 001-001, 001-002 | Core provider and jobs |
| 044-generation-reliability | DDD | 001-003, 001-004, 001-005 | History, retries and usage |

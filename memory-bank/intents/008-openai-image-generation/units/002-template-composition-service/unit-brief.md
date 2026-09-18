---
unit: 002-template-composition-service
intent: 008-openai-image-generation
phase: inception
status: complete
created: 2026-09-17T01:23:26.000Z
updated: 2026-09-17T01:23:26.000Z
---

# Unit Brief: Template and Composition Service

## Purpose

Gestionar plantillas comunes y privadas y convertir una generación en una versión final con SKU exacto y configuración reproducible.

## Scope

### In Scope
- CRUD/archive staff de plantillas y versionado.
- Campos opcionales, referencias y snapshot efectivo.
- Composición determinista de SKU y versiones no destructivas.

### Out of Scope
- Inferencia OpenAI y colas de trabajos.
- Editor libre tipo lienzo y códigos QR/barras.

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-3 | Plantillas comunes y privadas | Must |
| FR-4 | Composición híbrida y SKU exacto | Must |
| FR-10 | Persistencia y regeneración | Must |

## Domain Concepts

| Entity | Description |
|--------|-------------|
| ImageTemplate | Configuración staff, scope, versión y estado |
| TemplateReference | Imagen de referencia opcional |
| CompositionSnapshot | Configuración efectiva asociada a un resultado |
| ProductOverlay | SKU y parámetros deterministas |

## Dependencies

- **Depends on**: 001-image-generation-service, media/storage.
- **Depended by**: 003-product-image-integration, 004-openai-generation-ui.
- **External**: MinIO (medium), product metadata (medium).

## Story Summary

- **Total Stories**: 3
- **Must Have**: 3
- **Should Have**: 0
- **Could Have**: 0

| Story ID | Title | Priority | Status |
|---|---|---|---|
| 001-template-lifecycle | Template lifecycle | Must | Planned |
| 002-composition-snapshot | Composition snapshot | Must | Planned |
| 003-deterministic-sku-composition | Deterministic SKU composition | Must | Planned |

## Success Criteria

- [ ] Plantillas comunes/privadas y snapshots históricos están aislados.
- [ ] El SKU se renderiza exactamente y no altera la imagen base.
- [ ] Archivar no rompe regeneración desde snapshots históricos.

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 045-template-lifecycle | DDD | 002-001, 002-002 | Templates and snapshots |
| 046-template-composition | DDD | 002-003 | Deterministic SKU compositor |

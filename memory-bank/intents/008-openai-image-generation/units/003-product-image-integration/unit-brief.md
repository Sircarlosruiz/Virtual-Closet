---
unit: 003-product-image-integration
intent: 008-openai-image-generation
phase: inception
status: complete
created: 2026-09-17T01:23:26.000Z
updated: 2026-09-17T01:23:26.000Z
---

# Unit Brief: Product Image Integration

## Purpose

Conectar Virtual Closet con productos de Virtual Closet y BFashion, entregando solo imágenes seleccionadas por staff y manteniendo sincronización idempotente.

## Scope

### In Scope
- Contrato server-to-server y vínculo explícito producto/mayorista.
- Entrada desde BFashion y consulta de estados/resultados.
- Selección manual, publicación, deduplicación y retry de sincronización.

### Out of Scope
- Ejecución de OpenAI.
- Administración de plantillas y UI de generación.
- Precios, inventario y publicación automática.

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-11 | Integración Virtual Closet–BFashion | Must |
| FR-12 | Selección y publicación manual | Must |

## Domain Concepts

| Entity | Description |
|--------|-------------|
| ProductLink | Asociación explícita y autorizada entre productos/tenants |
| PublicationSelection | Decisión staff sobre un resultado |
| SyncDelivery | Estado idempotente de entrega por destino |

## Dependencies

- **Depends on**: 001 generation results, 002 snapshots, BFashion product/image contract.
- **Depended by**: 004-openai-generation-ui.
- **External**: BFashion Django REST (high), network/auth (high).

## Story Summary

- **Total Stories**: 3
- **Must Have**: 3
- **Should Have**: 0
- **Could Have**: 0

| Story ID | Title | Priority | Status |
|---|---|---|---|
| 001-product-generation-bridge | Product generation bridge | Must | Planned |
| 002-publication-selection | Publication selection | Must | Planned |
| 003-sync-delivery | Sync delivery | Must | Planned |

## Success Criteria

- [ ] Una solicitud desde BFashion crea un trabajo en Virtual Closet.
- [ ] Solo selección explícita publica en cada destino.
- [ ] Reintentos no duplican imágenes ni trabajos.
- [ ] Cross-tenant/product mismatches fail closed.

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 047-product-generation-bridge | Simple | 003-001 | Cross-system command/status |
| 048-product-publication-sync | Simple | 003-002, 003-003 | Manual publication and delivery |

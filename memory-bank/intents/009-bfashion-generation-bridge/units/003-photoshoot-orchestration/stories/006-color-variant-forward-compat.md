---
id: 006-color-variant-forward-compat
unit: 003-photoshoot-orchestration
intent: 009-bfashion-generation-bridge
status: complete
priority: should
created: 2026-09-18T10:40:00.000Z
assigned_bolt: 054-photoshoot-orchestration
implemented: true
---

# Story: 006-color-variant-forward-compat

## User Story

**As a** diseñador de la segunda pasada de variantes de color
**I want** que el modelo de datos de V1 ya tenga un asiento reservado para asociar un resultado a una variante concreta
**So that** cuando se implemente la generación por variante, no haga falta una migración destructiva de `photoshoots`, `generation_jobs`, `publication_selections` ni `product_links`

## Acceptance Criteria

- [ ] **Given** el modelo `Photoshoot`, **When** inspecciono su esquema, **Then** existe una columna `variant_key` nullable, `null` en todo disparo de V1
- [ ] **Given** el modelo `PhotoshootResult`, **When** inspecciono su esquema, **Then** también existe `variant_key` nullable, coherente con el del `Photoshoot` padre
- [ ] **Given** el estado agregado de un photoshoot (`004-aggregate-status-and-candidates`), **When** lo consulto, **Then** `variant_key` se devuelve explícitamente, aunque sea `null`
- [ ] **Given** la restricción de unicidad de `publication_selections` (`product_link_id`, `generation_job_id`, `composition_version_id`), **When** se diseña, **Then** admite —sin cambio de esquema— que dos variantes del mismo producto tengan selecciones independientes, porque cada variante produce `generation_job_id` distintos
- [ ] **Given** este intent, **When** se revisa su alcance, **Then** no se implementa ninguna lógica de negocio de variantes: filtrado por color, agrupación en la galería o resolución de `ProductVariant` de BFashion quedan fuera

## Technical Notes

- Esta historia es deliberadamente pequeña: el objetivo es que la segunda pasada no obligue a migrar, no construir la segunda pasada.
- `variant_key` se define como texto libre (no FK), porque `ProductVariant(color_label)` vive en BFashion y Virtual Closet no debe modelar el catálogo de colores del ecommerce externo.
- Verificar explícitamente que `uq_publication_selections_candidate` con `postgresql_nulls_not_distinct=True` no colisiona cuando dos variantes comparten `product_link_id` pero difieren en `generation_job_id`: como cada variante produce su propio `GenerationJob`, no hay colisión, pero conviene dejarlo probado.

## Dependencies

### Requires
- `001-photoshoot-submission` (el campo se define en el mismo modelo)

### Enables
- La futura segunda pasada de variantes de color (fuera de este intent)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Un disparo de V1 envía `variant_key` por error | Se acepta y se persiste, pero ninguna lógica de V1 lo usa para filtrar ni agrupar |
| Migración Alembic de este campo | Debe ser aditiva (columna nullable), sin backfill destructivo |

## Out of Scope

- Generación por variante de color
- Resolución o validación de `ProductVariant` de BFashion
- UI o filtrado por color en cualquier lado

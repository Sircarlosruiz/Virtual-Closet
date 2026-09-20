---
id: 006-product-slug-overlay-fit
unit: 004-replicate-execution-reliability
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:55:00.000Z
assigned_bolt: 055-replicate-execution-reliability
implemented: true
---

# Story: 006-product-slug-overlay-fit

## User Story

**As a** staff que superpone el identificador del producto sobre la imagen generada
**I want** que un slug de producto largo (`blusa-manga-globo`) se comporte de forma predecible con el compositor determinista
**So that** nunca aparezca un texto recortado, escalado en silencio o fuera del lienzo, y sepa con certeza si el overlay funcionó o quedó bloqueado

## Acceptance Criteria

- [ ] **Given** un slug real de BFashion de más de 30 caracteres, **When** se dispara un photoshoot con overlay, **Then** el texto normalizado se valida contra `SKU_MAX_LENGTH` en el disparo, no a mitad del pipeline
- [ ] **Given** ese slug con la configuración de `placement`/`style` pedida, **When** `evaluate_fit` lo mide, **Then** si no cabe, la `CompositionVersion` queda en `status: "blocked"` con `fit_result` reportando las dimensiones requeridas frente a las disponibles
- [ ] **Given** una `CompositionVersion` `blocked`, **When** consulto el photoshoot, **Then** el `GenerationJob` base sigue apareciendo como candidato publicable: el overlay bloqueado no destruye la generación
- [ ] **Given** el estado agregado de un photoshoot, **When** un resultado tiene overlay `blocked`, **Then** la respuesta distingue explícitamente «overlay bloqueado» de «generación fallida»
- [ ] **Given** un slug que sí cabe, **When** se renderiza, **Then** el texto queda completo y dentro de la imagen, verificado con la misma medición que decidió que cabía (`sku_renderer` comparte medición y render, NFR-3 del intent 008)
- [ ] **Given** la validación previa a entrega (NFR-7), **When** se ejecuta con al menos un slug real de más de 30 caracteres, **Then** el resultado (ajustado o `blocked`) queda documentado como evidencia

## Technical Notes

- No se cambia la semántica determinista de `sku_renderer.py` ni `composition_spec.py` en esta historia: se **verifica** el comportamiento existente contra el dato real (slugs, no SKUs cortos) y se documenta si el resultado es aceptable.
- Si al medir slugs reales la mayoría queda `blocked` con la configuración por defecto, **no se cambia la política de ajuste dentro de esta historia**: se escala como decisión de producto (**OQ-1** en requirements.md), porque cualquier alternativa (ajuste automático de tamaño, dos líneas) altera `spec_hash` y la semántica de ADR-054.
- `SUPPORTED_FONTS = {"default"}` con `ImageFont.load_default` es la única fuente disponible hoy; no se introduce una fuente nueva en esta historia.

## Dependencies

### Requires
- `003-generation-job-materialization` (unidad `003`, para tener imágenes base reales sobre las que componer)

### Enables
- Ninguna (cierra la unidad junto con `005`)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Slug con guiones y sin espacios (`blusa-manga-globo`) | Se normaliza igual que cualquier texto: `normalize_sku` no depende de la semántica de un SKU, solo de caracteres visibles |
| Slug que excede `SKU_MAX_LENGTH` (200) | Se rechaza en el disparo del photoshoot, `422`, antes de encolar nada |
| `placement.max_width` no configurado | Se usa el ancho disponible de la imagen menos el offset, igual que hoy |
| Dos slugs distintos con el mismo `spec_hash` por coincidencia | No debería ocurrir: `spec_hash` incluye el texto normalizado; se prueba como regresión de `compute_spec_hash` |

## Out of Scope

- Ajuste automático de tamaño de fuente o texto multilínea (requieren decisión de producto, ver OQ-1)
- Fuentes adicionales a `default`
- Editor visual de posición del overlay

---
id: 002-catalog-isolation-and-freshness
unit: 005-photoshoot-catalog
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T11:52:00.000Z
assigned_bolt: 056-photoshoot-catalog
implemented: true
---

# Story: 002-catalog-isolation-and-freshness

## User Story

**As a** backend de BFashion consultando el catálogo cada vez que el staff abre la pantalla de photoshoot
**I want** que el catálogo nunca filtre datos de otro tenant y que pueda saber sin descargar todo el cuerpo si cambió desde la última consulta
**So that** el aislamiento entre mayoristas se mantenga y la pantalla del staff no tenga que recomputar ni retransferir el catálogo completo en cada apertura

## Acceptance Criteria

- [ ] **Given** un `ServiceClient` de un tenant distinto, **When** consulta el catálogo de un producto que no le pertenece, **Then** recibe `403`/`404` sin filtrar si el producto existe
- [ ] **Given** un vínculo inactivo, **When** se consulta el catálogo, **Then** recibe `404`, coherente con el resto del puente
- [ ] **Given** dos consultas consecutivas sin cambios en plantillas ni modelos, **When** la segunda incluye `If-None-Match` con el `ETag` de la primera, **Then** recibe `304` sin cuerpo
- [ ] **Given** una plantilla activa modificada entre dos consultas, **When** se repite la consulta, **Then** `catalog_version` (y el `ETag` derivado) cambian, y un `If-None-Match` con el valor anterior ya no produce `304`
- [ ] **Given** un modelo nuevo dado de alta por el mayorista entre dos consultas, **When** se repite la consulta, **Then** aparece en `models[]` y `catalog_version` refleja el cambio
- [ ] **Given** cabeceras de servicio ausentes o inválidas, **When** se consulta el catálogo, **Then** recibe `401` sin evaluar ningún dato de catálogo

## Technical Notes

- `catalog_version` se calcula a partir de un agregado barato (por ejemplo, el máximo `updated_at` entre plantillas activas y modelos del mayorista, o un hash de esos identificadores + versiones), no de un contador mantenido a mano en una tabla nueva.
- El soporte de `ETag`/`If-None-Match` es a nivel de aplicación (calculado en el router a partir de `catalog_version`), no requiere infraestructura de caché nueva.
- Esta historia es la que prueba explícitamente FR-15 (fail-closed transversal) para esta unidad, igual que `003-source-image-rejection` lo hace para la unidad `002`.

## Dependencies

### Requires
- `001-photoshoot-options-catalog`

### Enables
- Ninguna (cierra la unidad)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `If-None-Match` con un valor que no corresponde a ningún `catalog_version` conocido | Se ignora como si no se hubiera enviado; se devuelve `200` con el catálogo completo |
| Dos tenants con productos y catálogos completamente distintos consultando "al mismo tiempo" | Cada uno recibe únicamente su propio catálogo; nunca hay fuga cruzada |
| Consulta durante la creación concurrente de una plantilla | Puede devolver el catálogo antes o después del alta, pero nunca un estado a medio escribir |

## Out of Scope

- Invalidación activa de caché del lado de BFashion (push/webhook): el modelo es de polling con `ETag`, no de notificación
- Métricas de tasa de acierto de caché

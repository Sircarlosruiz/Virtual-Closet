---
id: 001-photoshoot-options-catalog
unit: 005-photoshoot-catalog
intent: 009-bfashion-generation-bridge
status: draft
priority: must
created: 2026-09-18T11:50:00Z
assigned_bolt: 056-photoshoot-catalog
implemented: false
---

# Story: 001-photoshoot-options-catalog

## User Story

**As a** backend de BFashion construyendo el formulario de disparo del photoshoot
**I want** consultar en una sola llamada qué plantillas, modelos, poses y valores de `cloth_type` existen de verdad en Virtual Closet para este producto
**So that** el formulario del staff no lleve opciones incrustadas a mano y nunca se desincronice de lo que Virtual Closet realmente tiene disponible

## Acceptance Criteria

- [ ] **Given** un vínculo activo, **When** llamo a `GET /api/integration/v1/products/{external_product_id}/photoshoot-options`, **Then** recibo `200` con `templates[]`, `models[]`, `cloth_types[]`, `background_suggestions[]`, `color_suggestions[]`, `max_pose_count` y `catalog_version`
- [ ] **Given** plantillas en `status: draft` o `archived`, **When** consulto el catálogo, **Then** no aparecen en `templates[]`
- [ ] **Given** una plantilla `common`, **When** consulto el catálogo, **Then** siempre aparece, independientemente del mayorista del vínculo
- [ ] **Given** una plantilla `private` de un mayorista distinto al del vínculo, **When** consulto el catálogo, **Then** no aparece
- [ ] **Given** los modelos del mayorista del vínculo, **When** consulto `models[]`, **Then** cada uno lista únicamente las poses (`front`/`side`/`back`) que realmente tienen foto cargada, no las tres por defecto
- [ ] **Given** `cloth_types[]`, **When** lo inspecciono, **Then** contiene exactamente `{upper_body, lower_body, dress}`, el mismo conjunto cerrado que valida `api/schemas/pose_sets.py` y `models/batch_job.py`
- [ ] **Given** `max_pose_count`, **When** lo leo, **Then** su valor es 3, coherente con `VALID_POSES` en `services/model_pose_service.py`
- [ ] **Given** `background_suggestions[]` y `color_suggestions[]`, **When** los inspecciono, **Then** son valores distintos usados por plantillas activas, y la respuesta los distingue explícitamente como sugerencias, no como un catálogo cerrado

## Technical Notes

- Endpoint agregado único (no uno por recurso): el consumidor es una sola pantalla; fragmentar multiplicaría round trips y superficie de contrato. Mismo razonamiento que `GET .../photoshoots/{id}` (FR-8).
- Reutilizar los repositorios existentes de plantillas (`ImageTemplateRepository` o equivalente), `ModelRepo` y `ModelPhotoRepo`/`MediaRepo`. No se introduce un modelo de datos nuevo.
- `cloth_types[]` puede ser una constante de aplicación (no requiere consulta a BD), pero se expone por el mismo endpoint para que BFashion tenga una única fuente de verdad y no la hardcodee tampoco.
- No requiere `staff_id`: es de solo lectura, siguiendo el precedente de los `GET` existentes del contrato B que no llaman a `authorize_staff`.

## Dependencies

### Requires
- `001-product-link-creation` (unidad `001-bridge-provisioning`)

### Enables
- Construcción del formulario de disparo en BFashion (fuera de este intent)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Mayorista sin ninguna plantilla privada ni modelos propios | `templates[]` solo trae las `common`; `models[]` puede venir vacío; el catálogo sigue siendo `200`, no un error |
| Un modelo con las 3 poses cargadas | `available_poses: ["front", "side", "back"]` |
| Un modelo con 0 poses cargadas (recién creado) | Aparece en `models[]` con `available_poses: []`; BFashion decide si lo oculta en su UI |
| Plantilla con `colors` en `null` | No aporta nada a `color_suggestions[]`; no rompe la agregación |

## Out of Scope

- Escritura o edición de plantillas, modelos o poses
- Búsqueda o filtrado por texto dentro del catálogo
- Previsualización de imágenes de referencia de la plantilla

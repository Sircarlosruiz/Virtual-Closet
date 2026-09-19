---
unit: 005-photoshoot-catalog
intent: 009-bfashion-generation-bridge
phase: inception
status: complete
unit_type: backend
default_bolt_type: ddd-construction-bolt
created: 2026-09-18T11:45:00.000Z
updated: 2026-09-18T11:45:00.000Z
---

# Unit Brief: photoshoot-catalog

## Purpose

Exponer, por API servidor-a-servidor de solo lectura, lo que BFashion necesita para poblar el formulario del staff **antes** de disparar un photoshoot: qué plantillas activas existen, qué modelos y poses hay disponibles, y qué valores admite `cloth_type`.

Este hueco no estaba en la propuesta de partida del brief ni en la primera pasada de este intent. Se detectó al verificar `FR-5` (disparo del photoshoot) contra las cuatro unidades ya definidas: `FR-5` exige `template_id`, `model_ids`, `pose_ids`/`pose_count` y `cloth_type` como entrada, pero ninguna unidad exponía cómo BFashion descubre esos valores. Sin este catálogo, el formulario tendría que llevar las opciones incrustadas a mano — el acoplamiento exacto que este contrato busca evitar — y se desincronizaría en cuanto alguien creara una plantilla nueva o diera de alta un modelo en Virtual Closet.

## Scope

### In Scope
- `GET /api/integration/v1/products/{external_product_id}/photoshoot-options`
- Agregación de plantillas activas (comunes + privadas del mayorista del vínculo), modelos del mayorista con sus poses reales, y el enum cerrado de `cloth_type`
- Sugerencias no exhaustivas de `background` y `colors`, derivadas de plantillas activas
- Señal de versión de catálogo (`catalog_version`) para que BFashion decida si refresca su copia en caché
- Fail-closed: mismo tratamiento de vínculo, tenant y mayorista que el resto del puente

### Out of Scope
- Cualquier endpoint de escritura sobre plantillas, modelos o poses: eso ya existe cookie-auth (`/api/templates`, `/api/models`, `/api/pose-sets`) y no se toca
- Un enum cerrado de `background`/`colors`: no existe en el dominio y no se inventa uno
- Caché distribuida o CDN: se admite `ETag`/`304` a nivel de aplicación, no infraestructura nueva
- Paginación: V1 asume un catálogo por mayorista de tamaño acotado

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-16 | Catálogo de opciones del photoshoot | Must |

Verifica además NFR-1 (latencia y cadencia de refresco) y NFR-6 (aislamiento).

---

## Domain Concepts

Esta unidad no introduce entidades nuevas. Lee entidades ya existentes:

### Key Entities (existentes, leídas)

| Entity | Description | Campos relevantes para el catálogo |
|--------|-------------|--------------------------------------|
| `ImageTemplate` | Plantilla reutilizable de composición | `scope`, `wholesaler_id`, `version`, `status`, `name`, `model`, `background`, `colors`, `rack` |
| `Model` | Identidad de modelo del mayorista, agrupa 1..3 poses | `id`, `mayorista_id`, `name` |
| `ModelPhoto` | Foto de pose de un modelo | `model_id`, `pose` (`front`\|`side`\|`back`) |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `get_photoshoot_options` | Agrega plantillas, modelos y valores admisibles para un producto | `ServiceClient`, `external_product_id`, `external_wholesaler_id?` | Bundle de catálogo (FR-16) |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 2 |
| Must Have | 2 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| `001-photoshoot-options-catalog` | Exponer plantillas, modelos, poses y `cloth_types` en un solo recurso | Must | Planned |
| `002-catalog-isolation-and-freshness` | Aislamiento fail-closed y versionado de caché | Must | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `001-bridge-provisioning` | La resolución del vínculo y el alcance por mayorista dependen de `ProductLink` creable por API |

### Depended By

Ninguna unidad de este intent depende técnicamente de esta. El consumidor es el formulario de BFashion (intent 020), que la necesita **antes** de poder construirse — ver la nota de orden de entrega en `units.md`.

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| BFashion (intent 020) | Consume este catálogo para poblar el formulario del staff | Alto — contrato nuevo, desarrollo paralelo, y es la pieza que el otro equipo necesita más temprano |

---

## Technical Context

### Suggested Technology

Servicio de agregación puro en `services/`, sin escritura. Reutiliza `ImageTemplateRepository`/`image_template_repo`, `ModelRepo`, `MediaRepo` (`ModelPhotoRepo`) existentes. No requiere Celery: es una consulta síncrona de request/response.

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| `ProductLinkService.resolve_active_link` | Resolución fail-closed de propiedad | Interno |
| `image_template_repo` | Plantillas activas, comunes y privadas del mayorista | Interno |
| `model_repo` / `ModelPhotoRepo` | Modelos y poses del mayorista | Interno |

### Data Storage

No introduce almacenamiento nuevo. Solo lectura sobre tablas existentes.

---

## Constraints

- Solo lectura: cero mutaciones de estado.
- No requiere `staff_id` ni `authorize_staff`, siguiendo el precedente ya establecido por los `GET` existentes del contrato B (`get_product_generation_job`, `list_product_publication_candidates`), que solo resuelven el vínculo.
- Las plantillas `draft` y `archived` nunca aparecen.
- Las plantillas `private` de otro mayorista nunca aparecen, aunque compartan tenant.
- `background`/`colors` se presentan explícitamente como sugerencias no exhaustivas, nunca como un catálogo cerrado.
- Ningún dato de otro tenant es alcanzable a través de este endpoint.

---

## Success Criteria

### Functional
- [ ] `GET .../photoshoot-options` devuelve plantillas activas, modelos con poses reales y el enum de `cloth_type` en una sola respuesta
- [ ] Las plantillas `common` siempre aparecen; las `private` solo si pertenecen al mayorista del vínculo
- [ ] `max_pose_count` refleja el límite real del dominio (3)
- [ ] Un vínculo inexistente, inactivo o de otro tenant responde `404`/`403` sin filtrar catálogo
- [ ] `catalog_version` cambia cuando cambia una plantilla activa o un modelo del mayorista

### Non-Functional
- [ ] p95 ≤ 1 s (NFR-1)
- [ ] Ningún dato de otro tenant es accesible (NFR-6)
- [ ] `ETag`/`304` disponible para evitar recomputar el catálogo en consultas repetidas

### Quality
- [ ] Cobertura de código > 80 %
- [ ] Todos los criterios de aceptación cubiertos por pruebas
- [ ] Revisión de código aprobada

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| `056-photoshoot-catalog` | ddd | 001, 002 | Catálogo de opciones consumible por BFashion antes de construir su formulario |

---

## Notes

El número de bolt (`056`) es posterior a los bolts `050`-`055` ya planeados porque los números son globales y secuenciales por orden de planeación, no por orden de ejecución. Esta unidad se ejecuta temprano — justo después de `050`, en paralelo con `051` y `052` — según la sección "Execution Order" de `units.md`. La razón para priorizarla no es una dependencia técnica de `003-photoshoot-orchestration` (que no la tiene), sino que BFashion necesita este contrato para empezar a construir su formulario.

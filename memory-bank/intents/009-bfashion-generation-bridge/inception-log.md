---
intent: 009-bfashion-generation-bridge
created: 2026-09-18T00:00:00Z
completed: 2026-09-18T21:37:59Z
status: complete
---

# Inception Log: 009-bfashion-generation-bridge

## Overview

**Intent**: Completar el puente servidor-a-servidor entre BFashion y Virtual Closet para que un staff de BFashion cree un producto subiendo una foto (prenda sobre modelo o prenda sola) y Virtual Closet genere, oriente y devuelva las imágenes de producto.
**Type**: brown-field (continuación de 008-openai-image-generation)
**Created**: 2026-09-18

## Artifacts Created

| Artifact | Status | File |
|----------|--------|------|
| Requirements | ✅ | requirements.md |
| System Context | ✅ | system-context.md |
| Units | ✅ | units.md |
| Unit Briefs | ✅ | units/{unit}/unit-brief.md (5) |
| Stories | ✅ | units/{unit}/stories/*.md (20) |
| Bolt Plan | ✅ | memory-bank/bolts/{050..056}-*/bolt.md (7) |

## Summary

| Metric | Count |
|--------|-------|
| Functional Requirements | 16 |
| Non-Functional Requirements | 7 |
| Units | 5 |
| Stories | 20 |
| Bolts Planned | 7 |

## Units Breakdown

| Unit | Stories | Bolts | Priority |
|------|---------|-------|----------|
| 001-bridge-provisioning | 3 | 1 (`050`) | Must |
| 002-source-image-intake | 3 | 1 (`051`) | Must |
| 003-photoshoot-orchestration | 6 | 2 (`053`, `054`) | Must (5) / Should (1) |
| 004-replicate-execution-reliability | 6 | 2 (`052`, `055`) | Must |
| 005-photoshoot-catalog | 2 | 1 (`056`) | Must |

## Decision Log

| Date | Decision | Rationale | Approved |
|------|----------|-----------|----------|
| 2026-09-18 | Generación a nivel producto en V1; variantes de color en segunda pasada | Decisión del dueño de producto, entregada como input del intent | Sí |
| 2026-09-18 | Un único tenant (BFashion); no se resuelve multi-tenancy | Decisión del dueño de producto | Sí |
| 2026-09-18 | Replicate es el proveedor de producción para este flujo | Decisión del dueño de producto | Sí |
| 2026-09-18 | Las imágenes se copian al bucket de BFashion vía URL de transferencia presignada (TTL 900s) | Contrato A ya implementado en `services/bfashion_sync_adapter.py`; se confirma sin cambios | Sí |
| 2026-09-18 | Orquestador `Photoshoot` nuevo (no cablear `vton` en `_get_provider`) | `product_overlays` y `publication_selections` solo reconocen candidatos anclados a `GenerationJob`; cablear `vton` dejaría dos modelos de job paralelos y no cubriría N poses ni el estado agregado | Sí |
| 2026-09-18 | Identidad de staff vía endpoint admin S2S (`POST /staff-identities` + `:revoke`) | Consumido por `manage.py link_staff_identity` del intent hermano; automatizable y auditable | Sí |
| 2026-09-18 | Subida S2S solo presign + confirm, sin fallback multipart | Decisión explícita del dueño de producto: un navegador que no alcanza MinIO es problema de despliegue, no de código | Sí |
| 2026-09-18 | Sin interfaz nueva en Virtual Closet | La UI del staff vive en BFashion (intent 020); Virtual Closet expone solo API S2S y scripts | Sí |
| 2026-09-18 | `generate_image_task` no debe exigir `OPENAI_API_KEY` para jobs de otro proveedor | Bloqueante de primera clase para despliegue Replicate-only; promovido a FR-10 explícito | Sí |
| 2026-09-18 | Concurrencia, timeouts y contabilidad de uso se tratan como NFR con criterios propios, no como notas al pie | Replicate es la decisión de producción; el diseño actual tiene forma de OpenAI (`_REQUEST_TIMEOUT_SECONDS=60`, `UsageAccountingService` con campos de tokens) | Sí |
| 2026-09-18 | BFashion no tiene SKU; estampa el slug del producto (texto largo, no código corto) | Dato del intent hermano (`search/models.py:81`); condiciona el fit del overlay (FR-11, OQ-1) | Sí |
| 2026-09-18 | Se añaden `POST /staff-identities` y `POST /staff-identities/{id}:revoke` al contrato C, ampliando la propuesta de partida del brief | El brief dejaba la identidad de staff sin resolver ("script, endpoint de admin, o invitación"); el dueño del producto decidió endpoint admin S2S | Sí — el dueño del producto la propaga al agente del intent hermano; no requiere acción adicional de este lado |
| 2026-09-18 | Se añade `GET /photoshoot-options` (FR-16) y la unidad `005-photoshoot-catalog` tras una primera pasada de Checkpoint 3 | El agente del intent hermano detectó, contra este mismo contrato, que `FR-5` exige `template_id`/`model_ids`/`pose_ids`/`cloth_type` sin que ninguna unidad expusiera cómo se descubren; hueco real, no una duda | Sí |
| 2026-09-18 | Catálogo de opciones como endpoint único agregado, no uno por recurso | Un solo consumidor (la pantalla del staff); fragmentar multiplicaría round trips y superficie de contrato, igual razón que ya aplicaba a `GET .../photoshoots/{id}` (FR-8) | Sí |
| 2026-09-18 | `cloth_type` se expone como catálogo cerrado; `background`/`colors` como sugerencias no exhaustivas | `cloth_type` es un enum cerrado y verificado en código (`upper_body\|lower_body\|dress`); `background`/`colors` son campos generativos de texto libre en `ImageTemplate` — FR-4 ya lo establecía. Inventar un enum cerrado para ellos sería falso frente al dominio | Sí |
| 2026-09-18 | El catálogo no requiere `staff_id`/`authorize_staff` | Es de solo lectura y sigue el precedente ya establecido por los `GET` existentes del contrato B (`get_product_generation_job`, `list_product_publication_candidates`), que solo resuelven el vínculo | Sí |

## Scope Changes

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2026-09-18 | Contrato C ampliado con 2 endpoints de `staff-identities` no listados en la propuesta de partida del brief | Necesarios para que `manage.py link_staff_identity` del intent hermano tenga un consumidor real | +1 unidad (`001-bridge-provisioning` pasa de cubrir solo `product-links` a cubrir también identidad de staff), +2 historias |
| 2026-09-18 | Contrato C ampliado con `GET /photoshoot-options` (FR-16); nueva unidad `005-photoshoot-catalog` | Cierra el OQ-3 del agente del intent hermano: `FR-5` exigía campos que ninguna unidad exponía como descubribles | +1 FR, +1 unidad, +2 historias, +1 bolt (`056`), priorizado temprano en la secuencia de ejecución (ver Execution Order en `units.md`) |

## Ready for Construction

**Checklist**:
- [x] All requirements documented
- [x] System context defined
- [x] Units decomposed
- [x] Stories created for all units
- [x] Bolts planned
- [x] Human review complete (Checkpoint 3 aprobado por el dueño del producto, 2026-09-18, incluido el catálogo FR-16)

## Next Steps

1. Checkpoint 3: revisión conjunta de requirements, contexto, unidades, historias y bolts (incorporado el catálogo, FR-16)
2. Checkpoint 4: confirmación para iniciar Construction
3. El dueño del producto propaga al intent hermano el contrato C final, incluyendo `staff-identities` (OQ-2, ya resuelto de este lado) y `photoshoot-options` (FR-16, cierra su OQ-3)
4. Construction: iniciar con `050-bridge-provisioning`, seguido en paralelo por `051-source-image-intake`, `052-replicate-execution-reliability` y `056-photoshoot-catalog`

## Dependencies

Orden de ejecución por dependencias:

```text
                           ┌──► 051-source-image-intake ──┐
                           │                               │
050-bridge-provisioning ───┼──► 056-photoshoot-catalog     ├──► 053-photoshoot-orchestration ──► 054-photoshoot-orchestration ──► 055-replicate-execution-reliability
                           │                               │
052-replicate-execution-reliability (paralelo, sin dep.) ──┘
```

`050` es la raíz. `051`, `052` y `056` pueden ejecutarse en paralelo tras `050` (`052` incluso desde el inicio, al no depender de nada). `056` se prioriza en este grupo temprano aunque no sea una dependencia técnica de `053`, porque el intent hermano necesita el catálogo para construir su formulario. `053` requiere `050`, `051` y `052` cerrados (no requiere `056`). `054` continúa `053`. `055` cierra el intent y requiere `054` completo, porque necesita photoshoots reales contra Replicate para verificar consumo y overlay.

## Preguntas abiertas que requieren decisión antes o durante Construction

| ID | Pregunta | Bloquea |
|----|----------|---------|
| OQ-1 | Política de ajuste del overlay cuando el slug no cabe en una línea (bloquear / ajustar tamaño / dos líneas) | **Resuelto para V1**: "bloquear y no romper" es el comportamiento por defecto (FR-11). Bolt `055` escala a decisión de producto solo si al medir slugs reales la mayoría queda `blocked`; no bloquea el arranque de Construction |
| OQ-2 | Confirmación cruzada con el intent hermano de la forma exacta de `staff-identities` | **Resuelto de este lado**: forma fijada en FR-2. El dueño del producto la propaga al agente del intent hermano; no bloquea Construction en Virtual Closet |
| OQ-3 (este intent) | Valor de producción del tope global de concurrencia contra Replicate | Bolt `052`, historia `003-global-concurrency-cap` (tiene valor de partida, no bloquea) |
| OQ-4 | Número de poses por defecto cuando BFashion no especifica `pose_ids` | Bolt `053`, historia `001-photoshoot-submission` (tiene valor de partida, no bloquea) |
| OQ-5 | Si los espejos de staff computan cuota mensual de mayorista | Bolt `050`, historia `002-staff-identity-provisioning` |

**Nota**: el OQ-3 del intent hermano (`020-ai-product-imagery-integration`), sobre cómo BFashion descubre el catálogo de opciones del photoshoot, queda **cerrado por este intent** con FR-16 y la unidad `005-photoshoot-catalog`. No es el mismo OQ-3 que el de la tabla de arriba, que es interno de este intent (concurrencia).

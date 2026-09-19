---
intent: 009-bfashion-generation-bridge
phase: inception
status: units-decomposed
updated: 2026-09-18T11:40:00Z
---

# Puente de generación BFashion ↔ Virtual Closet — Unit Decomposition

## Units Overview

Este intent se descompone en **5 unidades de backend**. Las cinco usan `ddd-construction-bolt`, incluida `005-photoshoot-catalog`: aunque no introduce modelo de datos nuevo, sigue el mismo tipo de bolt que el resto de unidades de esta intent para consistencia de proceso, y su etapa de modelo confirma explícitamente que no hace falta revisión Alembic.

**Nota de revisión**: `005-photoshoot-catalog` se incorporó tras una primera pasada de Checkpoint 3, al detectarse que `FR-5` exige campos (`template_id`, `model_ids`, `pose_ids`/`pose_count`, `cloth_type`) que ninguna unidad exponía como descubribles por BFashion. Ver `requirements.md` FR-16 y la entrada correspondiente en `inception-log.md`.

### Unit 001: bridge-provisioning

**Description**: Alta y baja por API servidor-a-servidor de las dos entidades que hoy solo se crean a mano con scripts: el vínculo explícito de producto y la identidad de staff espejo. Sin esta unidad, el flujo pedido —que el staff cree el producto desde BFashion— es imposible.

**Assigned Requirements**: FR-1, FR-2, FR-15

**Stories**:
- `001-product-link-creation`: Crear un `ProductLink` por el puente, idempotente
- `002-staff-identity-provisioning`: Aprovisionar el `Mayorista` espejo y devolver su UUID
- `003-staff-identity-revocation`: Revocar el espejo sin perder trazabilidad histórica

**Deliverables**:
- `POST /api/integration/v1/product-links`
- `POST /api/integration/v1/staff-identities`
- `POST /api/integration/v1/staff-identities/{external_staff_id}:revoke`
- Nuevo modelo `StaffIdentityLink` + revisión Alembic
- Extensión de `ProductLinkService` con creación idempotente

**Dependencies**: Depende de: ninguna. Depended by: 002, 003, 005

**Estimated Complexity**: M

---

### Unit 002: source-image-intake

**Description**: El camino de subida servidor-a-servidor (G1, el hueco central). Entrega una URL presignada, verifica el objeto real tras la subida directa y registra la media reutilizando los servicios existentes. Los bytes no atraviesan ningún backend.

**Assigned Requirements**: FR-3, FR-4, FR-15

**Stories**:
- `001-source-image-presign`: Emitir la URL presignada y reservar la imagen de origen
- `002-source-image-confirm`: Verificar el objeto y registrar la media como `ready`
- `003-source-image-rejection`: Rechazos fail-closed y discrepancias declarado/real

**Deliverables**:
- `POST /api/integration/v1/products/{external_product_id}/source-images:presign`
- `POST /api/integration/v1/products/{external_product_id}/source-images/{source_image_id}:confirm`
- Nuevo modelo `BridgeSourceImage` + revisión Alembic
- Servicio de admisión que delega en `prenda_service` / `media_service` / `tryoff_source_image_service`

**Dependencies**: Depende de: 001 (necesita un `ProductLink` creable por API). Depended by: 003

**Estimated Complexity**: M

---

### Unit 003: photoshoot-orchestration

**Description**: El agregado `Photoshoot`: recibe **qué** quiere el staff, decide **qué pipeline** ejecutar, coordina `tryoff → vton → poses → composición` sobre los servicios existentes, materializa cada resultado como un `GenerationJob` publicable y expone un único estado agregado con sus candidatos.

Es la unidad que cierra G2. La razón por la que los resultados se materializan como `GenerationJob` y no como un tipo de resultado nuevo es estructural: `product_overlays` tiene `UNIQUE(generation_job_id)` y `publication_selections` es única por `(product_link_id, generation_job_id, composition_version_id)`, de modo que el camino de publicación ya entregado solo reconoce candidatos anclados a `GenerationJob`.

**Assigned Requirements**: FR-5, FR-6, FR-7, FR-8, FR-12, FR-13, FR-14

**Stories**:
- `001-photoshoot-submission`: Disparo validado, `202` y `expected_results`
- `002-stage-pipeline-execution`: Ejecución por etapas según `input_kind`
- `003-generation-job-materialization`: N resultados como candidatos publicables
- `004-aggregate-status-and-candidates`: Estado agregado y candidatos en una consulta
- `005-photoshoot-idempotency-and-retry`: Sin jobs ni imágenes duplicadas
- `006-color-variant-forward-compat`: Asiento reservado para la segunda pasada

**Deliverables**:
- `POST /api/integration/v1/products/{external_product_id}/photoshoots`
- `GET /api/integration/v1/products/{external_product_id}/photoshoots/{photoshoot_id}`
- Nuevos modelos `Photoshoot` y `PhotoshootStage` (+ `variant_key` reservado) + revisión Alembic
- `PhotoshootOrchestrationService` y sus tasks Celery
- Derivación del estado agregado a partir de etapas y resultados

**Dependencies**: Depende de: 001, 002, 004. Depended by: ninguna

**Estimated Complexity**: XL

---

### Unit 004: replicate-execution-reliability

**Description**: Hacer que el worker de generación sea realmente utilizable en un despliegue Replicate-only. Cubre el bloqueante de la credencial de OpenAI, el cableado del proveedor, el tope global de concurrencia que hoy no existe, los tiempos de espera acordes a latencias de minutos, la contabilidad de uso con forma de Replicate y el comportamiento del overlay ante el slug largo de BFashion.

**Assigned Requirements**: FR-9, FR-10, FR-11

**Stories**:
- `001-replicate-provider-wiring`: Resolver el proveedor de Replicate en el worker
- `002-provider-credential-gating`: Comprobación de credencial por proveedor (bloqueante)
- `003-global-concurrency-cap`: Tope global configurable de llamadas simultáneas
- `004-provider-timeout-policy`: Timeouts por proveedor acordes a minutos
- `005-replicate-usage-accounting`: Normalización de uso con forma de Replicate
- `006-product-slug-overlay-fit`: Overlay predecible con texto largo

**Deliverables**:
- `_get_provider` y la guarda de credencial de `tasks/image_generation.py` reescritas por proveedor
- Servicio de tope global de concurrencia
- Timeouts configurables por proveedor en `core/config.py`
- `UsageAccountingService` ampliado
- Política de ajuste del overlay verificada con slugs reales

**Dependencies**: Depende de: ninguna. Depended by: 003

**Estimated Complexity**: L

---

### Unit 005: photoshoot-catalog

**Description**: Catálogo de solo lectura que expone lo que BFashion necesita para poblar el formulario del staff antes de disparar un photoshoot: plantillas activas, modelos disponibles con sus poses reales, y el conjunto cerrado de valores admisibles de `cloth_type`. Cierra un hueco detectado tras el primer borrador de Checkpoint 3 por el agente del intent hermano contra este mismo contrato: `FR-5` exige esos campos como entrada, pero ninguna unidad exponía cómo se descubren. Sin este catálogo, BFashion tendría que incrustar las opciones a mano en su formulario, acoplándose exactamente a lo que el contrato busca evitar, y desincronizándose en cuanto se creara una plantilla nueva aquí.

**Decisión de diseño**: un único endpoint agregado (`GET .../photoshoot-options`), no uno por recurso — el consumidor real es una sola pantalla, y fragmentar multiplicaría los round trips y la superficie de contrato. `cloth_type` se expone como catálogo cerrado y autoritativo (enum verificado en código); `background` y `colors` se exponen como sugerencias no exhaustivas derivadas de plantillas activas, porque son campos generativos de texto libre, no un catálogo cerrado real (FR-4 ya lo establece).

**Assigned Requirements**: FR-16

**Stories**:
- `001-photoshoot-options-catalog`: Exponer plantillas, modelos, poses y `cloth_types` en un solo recurso
- `002-catalog-isolation-and-freshness`: Aislamiento fail-closed y versionado de caché

**Deliverables**:
- `GET /api/integration/v1/products/{external_product_id}/photoshoot-options`
- Servicio de agregación de catálogo, sin nuevo modelo de datos (lee `ImageTemplate`, `Model`, `ModelPhoto` existentes)
- Revisión Alembic: ninguna esperada (no introduce esquema nuevo), a confirmar en la etapa de modelo

**Dependencies**: Depende de: 001. Depended by: ninguna (consumo externo por BFashion)

**Estimated Complexity**: S

---

## Requirement-to-Unit Mapping

| FR | Requisito | Unidad |
|----|-----------|--------|
| FR-1 | Creación de vínculo de producto por el puente | `001-bridge-provisioning` |
| FR-2 | Aprovisionamiento y revocación de identidad de staff espejo | `001-bridge-provisioning` |
| FR-3 | Solicitud de subida presignada | `002-source-image-intake` |
| FR-4 | Confirmación y registro de la imagen de origen | `002-source-image-intake` |
| FR-5 | Disparo del photoshoot | `003-photoshoot-orchestration` |
| FR-6 | Orquestación por etapas | `003-photoshoot-orchestration` |
| FR-7 | Materialización como candidato publicable | `003-photoshoot-orchestration` |
| FR-8 | Estado agregado y candidatos | `003-photoshoot-orchestration` |
| FR-9 | Ejecución contra Replicate | `004-replicate-execution-reliability` |
| FR-10 | Worker sin credencial de OpenAI (bloqueante) | `004-replicate-execution-reliability` |
| FR-11 | Overlay con texto largo | `004-replicate-execution-reliability` |
| FR-12 | Idempotencia y reintento del photoshoot | `003-photoshoot-orchestration` |
| FR-13 | Publicación manual reutilizando el camino existente | `003-photoshoot-orchestration` |
| FR-14 | Preparación para variantes de color | `003-photoshoot-orchestration` |
| FR-15 | Fail-closed transversal | `001-bridge-provisioning`, `002-source-image-intake` (verificado); transversal al resto |
| FR-16 | Catálogo de opciones del photoshoot | `005-photoshoot-catalog` |

Los 16 FR están asignados. Ningún FR queda sin unidad.

| NFR | Unidad que lo verifica |
|-----|------------------------|
| NFR-1 Latencia S2S y polling | `001`, `002`, `003`, `005` |
| NFR-2 Tope global de concurrencia | `004` |
| NFR-3 Timeouts acordes a Replicate | `004` |
| NFR-4 Contabilidad de uso | `004` |
| NFR-5 Durabilidad e integridad | `003` |
| NFR-6 Aislamiento y credenciales | `001`, `002`, `003`, `004`, `005` |
| NFR-7 Verificabilidad visual y de overlay | `003`, `004` |

---

## Por qué no hay unidad de frontend

`memory-bank/project.yaml` declara `project_type: full-stack-web`, y el catálogo de tipos de proyecto crea por defecto una unidad `{intent}-ui` para los intents de este proyecto. **Aquí se omite deliberadamente.**

Razón: este intent no tiene superficie de usuario en Virtual Closet. La pantalla donde el staff sube el archivo, elige características, sigue el progreso y selecciona resultados vive en la administración de BFashion, y la construye el intent hermano `020-ai-product-imagery-integration`. Virtual Closet expone exclusivamente API servidor-a-servidor y scripts de operación.

Decisión confirmada por el dueño del producto en Checkpoint 1. Queda registrada aquí para que la ausencia de unidad de frontend se lea como una decisión y no como un olvido. Si más adelante se quisiera una vista de observabilidad del puente dentro de Virtual Closet (photoshoots, estados agregados, errores de entrega), sería un intent o una unidad posterior, no parte de este alcance.

---

## Unit Dependency Graph

```text
                          ┌──────► [002-source-image-intake] ──────┐
                          │                                        │
[001-bridge-provisioning] ┼──────► [005-photoshoot-catalog]        ├──► [003-photoshoot-orchestration]
                          │                                        │
                          └──────────────────────────────────────  │
                                                                    │
[004-replicate-execution-reliability] ─────────────────────────────┘
```

- `001` no depende de nada y desbloquea todo lo demás: sin `ProductLink` creable por API y sin identidad de staff, ningún otro endpoint del contrato C es utilizable end-to-end.
- `002` necesita `001` porque el presign se resuelve contra un `ProductLink`.
- `005` necesita `001` por la misma razón (resolución de vínculo y alcance del mayorista), pero es independiente de `002` y de `004`: es una unidad de solo lectura sobre `ImageTemplate`/`Model`/`ModelPhoto`, no toca subida de media ni ejecución de proveedor.
- `004` es independiente de `001`, `002` y `005`: es trabajo de worker y configuración. Puede desarrollarse en paralelo.
- `003` depende técnicamente de `001`, `002` y `004` para ejecutar el pipeline real. **No depende técnicamente de `005`**: el disparo del photoshoot valida `template_id`/`model_ids` contra los mismos repositorios que el catálogo lee, sin necesitar que el endpoint de catálogo exista. La razón para construir `005` temprano es de **orden de entrega entre equipos**, no de dependencia técnica: BFashion necesita el catálogo para construir su formulario antes de que el staff pueda disparar nada.

No hay dependencias circulares.

## Execution Order

1. **Primero**: `001-bridge-provisioning` — desbloquea el resto del contrato C.
2. **En paralelo, justo después**: `002-source-image-intake`, `005-photoshoot-catalog` y `004-replicate-execution-reliability` — sin dependencia entre sí. `005` se prioriza en este grupo aunque no sea un bloqueante técnico de `003`, porque BFashion necesita el catálogo para construir su formulario antes de tener nada que enviar en el disparo.
3. **Último**: `003-photoshoot-orchestration` — integra `001`, `002` y `004`, y es la unidad más grande.

La unidad `003` se parte en dos bolts, y la `004` también, para respetar el límite de 5-6 historias por bolt y para que el bolt de overlay con slugs reales se ejecute cuando ya existan imágenes generadas de verdad contra las que medir. `005` es lo bastante pequeña para un único bolt.

**Nota sobre numeración de bolts**: el bolt de `005-photoshoot-catalog` recibe el siguiente número global disponible (`056`), posterior a los bolts `050`-`055` ya planeados. El número no refleja su orden de ejecución — que es temprano, según esta sección — sino su orden de planeación. La secuencia real de trabajo se gobierna por `requires_bolts`/`enables_bolts` en cada `bolt.md`, no por el valor numérico del identificador.

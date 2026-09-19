---
intent: 009-bfashion-generation-bridge
phase: inception
status: inception-complete
created: 2026-09-18T09:00:00Z
updated: 2026-09-18T21:37:59Z
---

# Requirements: Puente de generación BFashion ↔ Virtual Closet

## Intent Overview

Completar el puente servidor-a-servidor que los bolts 047 y 048 dejaron construido a medias, para que un usuario con permiso de staff del ecommerce BFashion pueda crear un producto subiendo un archivo de imagen —una prenda puesta sobre una modelo, o una prenda sola sin modelo— y que Virtual Closet genere a partir de ese archivo las imágenes de producto con las características que el staff pida: modelo, poses, fondo, colores y superposición del identificador del producto.

Virtual Closet es la **única autoridad de generación**. BFashion nunca ejecuta inferencia. Este intent cubre **exclusivamente el lado Virtual Closet**; el lado BFashion lo cubre el intent hermano `020-ai-product-imagery-integration`, que se desarrolla en paralelo sobre `~/dev/bfashion/ecommerce`.

Continuación natural de `008-openai-image-generation`, cuyo alcance ya declaraba que «el staff puede iniciar trabajos desde Virtual Closet o desde la administración del ecommerce BFashion». Ampliación de la plataforma existente (brown-field).

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| El staff de BFashion crea un producto subiendo una sola foto y obtiene imágenes de producto | Un photoshoot end-to-end completa desde BFashion sin intervención manual en Virtual Closet | Must |
| Virtual Closet ejecuta el pipeline real (no solo `text`) desde el puente | Un photoshoot disparado por el puente produce N resultados publicables, no un job en `failed` | Must |
| El consumidor externo puede seguir el progreso de un trabajo de minutos | Un único `GET` devuelve estado agregado y candidatos sin sondear cinco recursos distintos | Must |
| Las imágenes elegidas llegan al bucket de BFashion sin duplicados ni pérdidas | Reintentar una entrega no duplica imágenes ni vuelve a llamar al proveedor | Must |
| La segunda pasada (variantes de color) no obliga a migrar lo construido en V1 | El modelo de V1 admite asociar un resultado a una variante sin cambio de esquema destructivo | Should |

---

## Decisiones tomadas por el dueño del producto

Son **entrada** de este intent, no preguntas abiertas.

1. **Generación por producto primero.** V1 genera a nivel producto. Las variantes de color son una segunda pasada posterior y no bloquean V1; el diseño debe admitirlas sin migración destructiva.
2. **Un solo tenant.** BFashion es un único tenant en Virtual Closet. No se resuelve multi-tenancy en este intent, pero tampoco se rompe el aislamiento existente.
3. **Replicate es el proveedor de producción.** Latencia de minutos. El flujo es asíncrono de verdad y el consumidor hace polling de un estado agregado.
4. **Las imágenes generadas se copian al bucket de BFashion.** Virtual Closet envía una URL presignada de transferencia (TTL 900 s) y BFashion se queda con su propia copia. El adaptador actual ya funciona así; se confirma, no se cambia.
5. **Orquestación (G2): orquestador Photoshoot nuevo.** Agregado nuevo con estado agregado y etapas `tryoff → vton → poses → composición`, que produce N filas `GenerationJob`. **No** se cablea `vton` dentro de `_get_provider` ni se hacen ambas por fases.
6. **Identidad del staff: endpoint admin servidor-a-servidor.** `POST /api/integration/v1/staff-identities` autenticado con `X-Service-Id` / `X-Service-Secret`. BFashion aprovisiona y revoca sus espejos por API y guarda el UUID devuelto.
7. **Subida (G1): solo presign + confirm.** Sin ruta multipart de respaldo. Si aparece un entorno donde el navegador no alcanza MinIO/S3, se trata como problema de despliegue, no como un segundo camino de código.
8. **Sin interfaz nueva en Virtual Closet.** La UI del staff vive en BFashion (intent 020). Virtual Closet expone solo API servidor-a-servidor y scripts.

---

## Evidencia verificada en el repositorio

Todo lo siguiente se comprobó leyendo el código de este repositorio antes de redactar los requisitos.

### Lo que ya existe y funciona

| Pieza | Ruta | Estado |
|-------|------|--------|
| Puente S2S (5 endpoints) | `backend/api/routers/integration.py` | Funciona |
| Autenticación de servicio fail-closed | `backend/core/dependencies.py:149` `get_service_client` | Funciona |
| Vínculo explícito producto↔propietario | `backend/models/product_link.py`, `services/product_link_service.py` | Funciona |
| Autorización de staff asertado | `backend/services/integration_service.py` `_authorize_staff` | Funciona |
| Selección y entrega idempotente | `services/publication_service.py`, `services/sync_delivery_service.py` | Funciona |
| Adaptador de salida a BFashion (contrato A) | `services/bfashion_sync_adapter.py` | Funciona |
| Presign de subida | `services/storage_service.py` `generate_upload_url` | Funciona |
| Precedente presign→confirm | `api/routers/prendas.py` (`GET /upload-url` + `POST ""`) | Funciona |
| Pipelines de IA reales | `tryoff`, `vton`, `batches`, `pose-sets`, `composition`, `templates` | Funcionan, con auth por cookie |
| Ruta Replicate | `services/vton/catvton_replicate_provider.py`, `services/providers/replicate_provider.py` | Existe |

### Huecos confirmados

- **G1 — No hay camino de subida por el puente.** `ImageGenerationRequest` (`api/schemas/image_generation.py`) solo acepta `garment_id`, `model_id` y `reference_image_ids`: UUIDs de media que ya vive en Virtual Closet. Todos los endpoints de subida son cookie-auth. BFashion no tiene forma de entregar bytes.
- **G2 — El puente crea un `GenerationJob` que el worker no sabe ejecutar.** `tasks/image_generation.py::_get_provider` solo devuelve `OpenAIImageProvider`, y `OpenAIImageProvider.generate` solo soporta `mode == "text"`: eleva `ProviderRequestError` para `edit`, `extraction` y `try_on`. Un job `try_on` disparado desde BFashion termina hoy en `failed`.
- **G3 — No se puede crear un `ProductLink` por el puente.** `api/routers/product_links.py` solo expone `GET /lookup` con auth por cookie. Crear un vínculo requiere ejecutar `scripts/link_product.py` a mano.
- **G4 — Replicate no está cableado a este flujo.** El camino Replicate existe para VTON, pero no para `generation_jobs`.
- **G5 — Variantes de color.** BFashion modela `ProductVariant(color_label)`; Virtual Closet solo conoce «colores» de plantilla y de overlay.

### Hallazgos adicionales que condicionan el diseño

1. **La publicación está anclada a `GenerationJob`.** `product_overlays` tiene `UNIQUE(generation_job_id)` y `publication_selections` es única por `(product_link_id, generation_job_id, composition_version_id)`. Los resultados de `vton_job`, `batch_job` y `pose_set` **no son candidatos publicables hoy**. Un photoshoot de N poses necesita N filas `GenerationJob` para producir N candidatos. Esta es la razón técnica que decide G2 a favor del orquestador nuevo.
2. **`generate_image_task` aborta si `OPENAI_API_KEY` está vacío**, incluso para un job cuyo proveedor es Replicate (`tasks/image_generation.py`, guarda de entrada del task). Bloqueante de primera clase para un despliegue Replicate-only.
3. **No existe tope global de concurrencia.** `ConcurrencyGuardService` es un *lease por job* (anti-duplicado de entrega), no un límite de N llamadas simultáneas al proveedor.
4. **`UsageAccountingService` tiene forma de OpenAI.** Filtra a `total_tokens`, `input_tokens`, `output_tokens` y sus detalles. Replicate reporta tiempo de predicción y métricas, no tokens: con la implementación actual el consumo quedaría siempre como `unknown`.
5. **`_REQUEST_TIMEOUT_SECONDS = 60`** en `services/image_generation_providers.py` no sirve para latencias de minutos.
6. **El compositor de overlay no parte líneas.** `services/sku_renderer.py::evaluate_fit` mide una sola línea con `SUPPORTED_FONTS = {"default"}` (`ImageFont.load_default`) y marca `blocked` si no cabe. `SKU_MAX_LENGTH = 200` en `composition_spec.py`. Como BFashion no tiene campo SKU y va a estampar el **slug del producto** (`search/models.py:81`), el texto entrante será largo y legible (`blusa-manga-globo`), no un código corto. Ver **OQ-1**.
7. **Ninguna unidad exponía cómo BFashion descubre plantillas, modelos, poses y valores de `cloth_type`.** `FR-5` (disparo del photoshoot) exige esos campos como entrada, pero antes de esta revisión no existía ningún endpoint de catálogo bajo `/api/integration/v1`. Sin él, el formulario del staff en BFashion tendría que llevar las opciones incrustadas a mano, acoplando exactamente lo que el contrato busca evitar, y desincronizándose en cuanto se creara una plantilla nueva. Cerrado por **FR-16**, detectado por el agente del intent hermano como su OQ-3.

---

## Contrato HTTP compartido

### A) Virtual Closet → BFashion — ya implementado aquí, **sin cambios**

```
PUT {BFASHION_BASE_URL}/internal/v1/products/{external_product_id}/images
Headers: X-Service-Id, X-Service-Secret, Idempotency-Key: <publication_selection_id>
Body:    publication_selection_id, generation_job_id, composition_version_id|null,
         storage_key, transfer_url (presignada 900 s), content_type,
         configuration (snapshot), staff_id
2xx {"id": ref} → synced | 409 {"id": ref} → duplicado, no es error | >=400 → fallo
```

Este intent **no toca** este contrato.

### B) BFashion → Virtual Closet — ya existe aquí, **sin cambios**

```
POST /api/integration/v1/products/generation-jobs
GET  /api/integration/v1/products/{external_product_id}/generation-jobs/{job_id}
GET  /api/integration/v1/products/{external_product_id}/generation-jobs/{job_id}/publication-candidates
POST /api/integration/v1/products/{external_product_id}/publications
GET  /api/integration/v1/products/{external_product_id}/publications/{publication_id}
POST /api/integration/v1/products/{external_product_id}/publications/{publication_id}/retry
```

### C) BFashion → Virtual Closet — **NUEVO, diseñado en este intent**

El intent hermano consume estos contratos. Cualquier cambio posterior debe anunciarse explícitamente.

```
POST /api/integration/v1/product-links
POST /api/integration/v1/staff-identities
POST /api/integration/v1/staff-identities/{external_staff_id}:revoke
POST /api/integration/v1/products/{external_product_id}/source-images:presign
POST /api/integration/v1/products/{external_product_id}/source-images/{source_image_id}:confirm
GET  /api/integration/v1/products/{external_product_id}/photoshoot-options
POST /api/integration/v1/products/{external_product_id}/photoshoots
GET  /api/integration/v1/products/{external_product_id}/photoshoots/{photoshoot_id}
```

**Diferencias respecto a la propuesta de partida del brief:**
- Se añaden los dos endpoints de `staff-identities`, que el brief dejaba sin resolver («script, endpoint de admin, o invitación»). Su forma se detalla en FR-2 porque el comando `manage.py link_staff_identity` del intent hermano los va a consumir.
- Se añade `GET .../photoshoot-options` (FR-16), ausente de la propuesta de partida y del alcance original de requirements.md hasta esta revisión. Cierra un hueco real detectado por el agente del intent hermano contra el propio contrato: `FR-5` (photoshoot submission) exige `template_id`, `model_ids`, `pose_ids`/`pose_count`, `cloth_type`, `background`, `colors` como entrada, pero ninguna unidad exponía cómo BFashion descubre esos valores. Sin este endpoint, el formulario del staff tendría que llevar las opciones incrustadas a mano.

Todos los endpoints de C exigen `X-Service-Id` + `X-Service-Secret` y son fail-closed.

---

## Functional Requirements

Todos los requisitos funcionales tienen prioridad **Must** salvo indicación contraria.

### FR-1: Creación de vínculo de producto por el puente
- **Descripción**: BFashion crea el `ProductLink` por API servidor-a-servidor, sin ejecutar `scripts/link_product.py` a mano. El flujo acordado es que BFashion cree primero un producto borrador y use su identificador como `external_product_id`.
- **Contrato**: `POST /api/integration/v1/product-links`. Entrada: `external_product_id`, `external_wholesaler_id` (opcional), `staff_id`, `prenda_id` (opcional). Salida: `product_link_id`, `external_product_id`, `mayorista_id`, `tenant_id`, `is_active`, `created`.
- **Aceptación**:
  - El `system` y el `tenant_id` se toman del `ServiceClient` autenticado, nunca del cuerpo de la petición.
  - Repetir la creación con el mismo `(system, external_product_id)` devuelve el vínculo existente con `created: false` y `200`, no un `500` por violación de la restricción única `uq_product_links_system_external_product`.
  - Si el mismo `(system, external_product_id)` existe pero apunta a otro tenant, se responde `403` y no se modifica nada.
  - El `staff_id` asertado se valida con la misma regla que el resto del puente: rol en `{admin, owner, staff}` y mismo tenant que el vínculo resultante. Un `staff_id` desconocido responde `403`.
  - El `mayorista_id` del vínculo se resuelve desde la identidad de staff espejo y el tenant del `ServiceClient`; nunca se deduce de un SKU ni de un identificador externo.
- **Related Stories**: `001-product-link-creation`

### FR-2: Aprovisionamiento y revocación de la identidad de staff espejo
- **Descripción**: Cada staff de BFashion (`django.contrib.auth.User`, PK entero) necesita un `Mayorista` espejo en Virtual Closet, porque `integration_service._authorize_staff` resuelve el actor contra la tabla `mayorista` por UUID. BFashion aprovisiona y revoca esos espejos por API y guarda el UUID devuelto en su tabla `StaffIntegrationIdentity(user OneToOne, virtual_closet_staff_id UUID)`.
- **Contrato**:
  - `POST /api/integration/v1/staff-identities` — Entrada: `external_staff_id` (string, PK de BFashion como texto), `email`, `display_name`, `role` (`staff` por defecto). Salida: `staff_id` (UUID del `Mayorista` espejo), `external_staff_id`, `email`, `role`, `is_active`, `created`.
  - `POST /api/integration/v1/staff-identities/{external_staff_id}:revoke` — Salida: `staff_id`, `external_staff_id`, `is_active: false`.
- **Aceptación**:
  - El consumidor previsto es el comando `manage.py link_staff_identity` del intent hermano, que llama al endpoint y persiste el UUID devuelto. No hay transcripción manual de UUIDs.
  - **Idempotente por `(system, external_staff_id)`**: reaprovisionar el mismo staff devuelve **el mismo** `staff_id` con `created: false`. Nunca crea un segundo espejo ni un segundo `Mayorista`.
  - El espejo se crea en el tenant del `ServiceClient` autenticado, con rol dentro de `{admin, owner, staff}`, de modo que `_authorize_staff` lo acepte sin modificarse.
  - Revocar marca el vínculo como inactivo. A partir de ahí, ese `staff_id` es rechazado por el resto de endpoints del puente con `403`, y el `Mayorista` espejo no se borra: la trazabilidad histórica de `publication_selections.selected_by` y `product_links.created_by` se conserva.
  - Revocar dos veces es idempotente y devuelve `200`.
  - El espejo no puede autenticarse por cookie con credenciales utilizables: no se emite contraseña conocida por BFashion ni se devuelve secreto alguno en la respuesta.
- **Related Stories**: `002-staff-identity-provisioning`, `003-staff-identity-revocation`

### FR-3: Solicitud de subida presignada por el puente
- **Descripción**: Virtual Closet entrega una URL presignada para que el navegador del staff suba el archivo directo al almacenamiento de Virtual Closet. Los bytes no atraviesan el backend de BFashion ni el de Virtual Closet.
- **Contrato**: `POST /api/integration/v1/products/{external_product_id}/source-images:presign`. Entrada: `staff_id`, `external_wholesaler_id` (opcional), `kind` (`garment_on_model` | `flat_garment`), `content_type`, `size_bytes`, `filename`. Salida: `source_image_id`, `upload_url`, `method: PUT`, `headers`, `expires_in`, `storage_key`.
- **Aceptación**:
  - Reutiliza `StorageService.generate_upload_url` y el precedente `/api/prendas/upload-url` + `POST /api/prendas`; no se introduce un mecanismo de almacenamiento nuevo.
  - Se rechazan antes de firmar: `content_type` fuera de `{image/jpeg, image/png}`, `size_bytes` por encima del límite configurado, y `kind` desconocido.
  - La URL caduca en un TTL configurable (propuesta: 900 s) y solo autoriza `PUT` sobre la clave emitida.
  - Se registra una fila de imagen de origen en estado `pending`, asociada al `product_link` resuelto y al `staff_id` autorizado. Antes de la confirmación no es utilizable para generar.
  - Vínculo ausente, inactivo, de otro tenant o de otro mayorista: `403`/`404` sin firmar nada.
  - La respuesta no contiene credenciales de almacenamiento ni de proveedor de IA.
- **Related Stories**: `001-source-image-presign`

### FR-4: Confirmación y registro de la imagen de origen
- **Descripción**: Tras la subida directa, BFashion confirma; Virtual Closet valida el objeto real y lo registra como media utilizable.
- **Contrato**: `POST /api/integration/v1/products/{external_product_id}/source-images/{source_image_id}:confirm`. Entrada: `staff_id`, `external_wholesaler_id` (opcional), `checksum_sha256` (opcional). Salida: `source_image_id`, `kind`, `status: ready`, `content_type`, `size_bytes`, `preview_url`.
- **Aceptación**:
  - Se verifica que el objeto existe en el almacenamiento (`StorageService.object_exists`) y que su tipo y tamaño reales coinciden con lo declarado en el presign. Una discrepancia deja la imagen en `rejected` con motivo, y no en `ready`.
  - La confirmación registra la media reutilizando los servicios existentes (`prenda_service` / `media_service` / `tryoff_source_image_service`) según el `kind`, en lugar de crear un cuarto almacén de imágenes de origen.
  - Confirmar dos veces la misma imagen ya `ready` es idempotente y devuelve el mismo `source_image_id` con `200`.
  - Confirmar una imagen que pertenece a otro `product_link` responde `403` y no la registra.
  - Confirmar sin que el objeto exista responde `409` con un código de error explícito; la imagen permanece `pending` y puede reintentarse tras subir.
- **Related Stories**: `002-source-image-confirm`, `003-source-image-rejection`

### FR-5: Disparo del photoshoot
- **Descripción**: BFashion dispara un único trabajo de alto nivel que describe **qué** quiere el staff, no qué pipeline ejecutar.
- **Contrato**: `POST /api/integration/v1/products/{external_product_id}/photoshoots`, con cabecera `Idempotency-Key`. Entrada: `staff_id`, `external_wholesaler_id` (opcional), `source_image_id`, `input_kind` (`garment_on_model` | `flat_garment`), `template_id` (opcional), `model_ids`, `pose_ids` o `pose_count`, `cloth_type`, `background`, `colors`, `overlay` (`text`, `placement`, `style`), `variant_key` (reservado, `null` en V1). Salida `202`: `photoshoot_id`, `status: queued`, `external_product_id`, `stages`, `expected_results`, `created_at`.
- **Aceptación**:
  - El `input_kind` determina el pipeline, no el cliente: BFashion nunca nombra `tryoff` ni `vton`.
  - Combinaciones no soportadas (sin modelos, `pose_count` fuera de rango, `cloth_type` desconocido, `source_image_id` no `ready`) se rechazan con `422` **antes** de encolar nada y antes de cualquier llamada al proveedor.
  - `expected_results` se calcula y se devuelve en el momento del disparo: el consumidor sabe cuántos candidatos esperar antes de que exista ninguno.
  - Se persiste una instantánea de la configuración efectiva (plantilla, modelos, poses, fondo, colores, overlay) junto al photoshoot, para poder regenerar y para acompañar la publicación.
  - Vínculo, tenant y staff se validan fail-closed con las mismas reglas del resto del puente.
- **Related Stories**: `001-photoshoot-submission`

### FR-6: Orquestación por etapas
- **Descripción**: Virtual Closet ejecuta el pipeline real en Celery según el tipo de entrada.
- **Aceptación**:
  - `garment_on_model` → `tryoff` (prenda plana) → `vton` sobre los modelos elegidos → `pose_set` (N poses) → `composición` (overlay).
  - `flat_garment` → `vton` directo → `pose_set` → `composición`. La etapa `tryoff` se marca `skipped`, no `failed`.
  - Cada etapa registra `status`, `started_at`, `completed_at` y `error_code`. Una etapa que falla no deja el photoshoot colgado en `running` de forma indefinida.
  - El fallo de una rama (un modelo, una pose) no cancela las demás: el photoshoot puede terminar en `partial` con los resultados que sí completaron.
  - La orquestación reutiliza los servicios existentes (`TryoffJobService`, `VTONJobService`, `PoseSetService`, `SkuCompositionService`); no se duplica lógica de inferencia.
  - Ninguna credencial de proveedor sale del contexto del worker.
- **Related Stories**: `002-stage-pipeline-execution`

### FR-7: Materialización de cada resultado como candidato publicable
- **Descripción**: Cada imagen producida por el photoshoot se materializa como una fila `GenerationJob` con `result_key` durable, para que el camino de publicación existente la reconozca sin cambios.
- **Aceptación**:
  - N poses × M modelos producen N×M filas `GenerationJob` completadas, cada una con `owner_id` = `product_link.mayorista_id` y `result_key` apuntando a un objeto durable del bucket `generated`.
  - Cada `GenerationJob` resultante es un candidato válido para `GET .../generation-jobs/{job_id}/publication-candidates` y para `POST .../publications`, sin modificar `publication_service.py` ni `sync_delivery_service.py`.
  - Las superposiciones de overlay se adjuntan como `CompositionVersion` sobre el `ProductOverlay` del `GenerationJob` correspondiente, respetando `UNIQUE(generation_job_id)` y `UNIQUE(overlay_id, spec_hash)`.
  - Un resultado no se marca completado hasta que su archivo está persistido; no existe un `GenerationJob` `completed` sin `result_key`.
- **Related Stories**: `003-generation-job-materialization`

### FR-8: Estado agregado y candidatos en una sola consulta
- **Descripción**: El consumidor sondea un único recurso para saber si puede mostrar la galería.
- **Contrato**: `GET /api/integration/v1/products/{external_product_id}/photoshoots/{photoshoot_id}`. Salida: `photoshoot_id`, `external_product_id`, `status` (`queued` | `running` | `partial` | `completed` | `failed`), `stages[]`, `expected_results`, `completed_results`, `failed_results`, `results[]` (`generation_job_id`, `status`, `preview_url`, `variant_key`), `candidates[]`, `error_code`.
- **Aceptación**:
  - `candidates[]` tiene la misma forma que `PublicationCandidateResponse`, para que BFashion no necesite dos lectores distintos.
  - El estado agregado se deriva de las etapas y de los resultados, no se mantiene a mano en dos sitios.
  - `completed` significa disponible para revisión, **nunca** publicado.
  - Consultar un photoshoot de otro producto o de otro tenant responde `404`/`403` sin filtrar existencia.
  - Las `preview_url` son de vida corta y regenerables; nunca se devuelve una clave de almacenamiento como si fuese pública.
- **Related Stories**: `004-aggregate-status-and-candidates`

### FR-9: Ejecución contra Replicate
- **Descripción**: Replicate es el proveedor cableado a este flujo en producción.
- **Aceptación**:
  - El worker de generación resuelve el proveedor de Replicate para los modos que este flujo usa; hoy `_get_provider` solo devuelve `OpenAIImageProvider`.
  - El proveedor elegido queda persistido por job y no se cambia silenciosamente si falla.
  - Se reutiliza la ruta Replicate existente (`services/vton/catvton_replicate_provider.py`, `services/providers/replicate_provider.py`) en lugar de escribir un cliente nuevo.
  - Sin `REPLICATE_API_KEY` válida se informa indisponibilidad de forma explícita antes de encolar; no se degrada a otro proveedor por su cuenta.
- **Related Stories**: `001-replicate-provider-wiring`

### FR-10: El worker arranca sin credencial de OpenAI
- **Descripción**: **Bloqueante.** `tasks/image_generation.py::generate_image_task` eleva `ValueError("Image generation is unavailable: provider is not configured")` si `OPENAI_API_KEY` está vacío, **antes** de mirar qué proveedor pide el job. En un despliegue Replicate-only, todo job falla.
- **Aceptación**:
  - La comprobación de credencial pasa a ser **por proveedor**: un job de Replicate requiere `REPLICATE_API_KEY` y no requiere `OPENAI_API_KEY`; un job de OpenAI requiere `OPENAI_API_KEY`.
  - Con `OPENAI_API_KEY` vacío y `REPLICATE_API_KEY` presente, un photoshoot completa end-to-end.
  - La ausencia de la credencial que el job sí necesita produce un fallo clasificado y no reintentable, con código de error distinguible de un fallo del proveedor.
  - Ninguna credencial aparece en respuestas HTTP ni en registros.
- **Related Stories**: `002-provider-credential-gating`

### FR-11: Superposición del identificador de producto con texto largo
- **Descripción**: BFashion no tiene campo SKU y estampa el **slug del producto** (`blusa-manga-globo`), no un código corto. El compositor debe comportarse de forma predecible con ese texto.
- **Aceptación**:
  - El texto entrante se normaliza con `normalize_sku` y se valida contra `SKU_MAX_LENGTH`; un texto que excede el límite se rechaza en el disparo del photoshoot, no a mitad del pipeline.
  - Si el texto no cabe con la configuración pedida, se registra una `CompositionVersion` en estado `blocked` con el motivo medido (ancho requerido frente a disponible) y **no** se produce una imagen con el texto recortado, escalado en silencio o fuera del lienzo.
  - Un photoshoot cuyo overlay queda `blocked` sigue exponiendo los resultados base como candidatos publicables: el fallo del overlay no destruye la generación.
  - La respuesta del estado agregado distingue «overlay bloqueado» de «generación fallida».
  - Ver **OQ-1**: si el ajuste a una línea con la fuente por defecto resulta ilegible para slugs largos reales, la política de ajuste requiere una decisión de producto.
- **Related Stories**: `006-product-slug-overlay-fit`

### FR-12: Idempotencia y reintento del photoshoot
- **Descripción**: Ni los trabajos ni las imágenes se duplican ante reintentos o entregas duplicadas del broker.
- **Aceptación**:
  - Repetir `POST .../photoshoots` con la misma `Idempotency-Key` y el mismo contenido devuelve el photoshoot existente sin crear uno nuevo ni encolar de nuevo.
  - La misma `Idempotency-Key` con contenido distinto responde `409`, siguiendo el comportamiento ya implementado en `IdempotencyService`.
  - Una entrega duplicada de mensaje durante la ejecución no inicia dos llamadas al proveedor para el mismo intento: el lease por job (`ConcurrencyGuardService`) se mantiene.
  - Reintentar una entrega de publicación no vuelve a generar ni duplica imágenes en BFashion: se conserva el `Idempotency-Key = publication_selection_id` del contrato A.
  - Un fallo de sincronización con BFashion **no** pierde un resultado ya generado: el `GenerationJob` y su `result_key` sobreviven y la entrega se reintenta desde lo persistido.
- **Related Stories**: `005-photoshoot-idempotency-and-retry`

### FR-13: Publicación manual y entrega, reutilizando el camino existente
- **Descripción**: Solo la selección explícita del staff publica. Nunca hay publicación automática.
- **Aceptación**:
  - Completar un photoshoot no crea ninguna `PublicationSelection`.
  - La selección y la entrega siguen usando `POST .../publications` y `SyncDeliveryService` tal como están; este intent no reescribe ese camino.
  - El contrato A permanece sin cambios: `PUT /internal/v1/products/{external_product_id}/images` con `Idempotency-Key = publication_selection_id`, `storage_key` durable y `transfer_url` presignada de 900 s.
  - Los destinos `virtual_closet` y `bfashion` mantienen su estado independiente: un fallo en uno no revierte el otro.
  - Un resultado privado de un mayorista no se vuelve público por una sincronización fallida.
- **Related Stories**: `004-aggregate-status-and-candidates`, `005-photoshoot-idempotency-and-retry`

### FR-14: Preparación para variantes de color (segunda pasada)
- **Descripción**: V1 genera a nivel producto. La segunda pasada asociará una imagen generada a una variante de color concreta del producto externo (`ProductVariant(color_label)` en BFashion).
- **Prioridad**: Should
- **Aceptación**:
  - El photoshoot y cada resultado admiten un identificador de variante opcional (`variant_key`), `null` en V1, persistido y devuelto en el estado agregado.
  - Añadir variantes en la segunda pasada no exige migración destructiva de `photoshoots`, `generation_jobs`, `publication_selections` ni `product_links`.
  - La restricción de unicidad de selección de publicación admite que dos variantes del mismo producto publiquen imágenes distintas sin colisionar.
  - No se implementa ninguna lógica de variantes en V1: solo se deja el asiento reservado y documentado.
- **Related Stories**: `006-color-variant-forward-compat`

### FR-15: Fail-closed transversal en todo el puente
- **Descripción**: Cross-tenant, cross-product y staff desconocido fallan cerrado, en todos los endpoints nuevos.
- **Aceptación**:
  - Todo endpoint del contrato C exige `X-Service-Id` + `X-Service-Secret` verificados contra el hash bcrypt, con `ServiceClient` y tenant activos.
  - `system` y `tenant_id` se derivan siempre del `ServiceClient`, nunca del cuerpo de la petición.
  - Un `staff_id` desconocido, revocado, sin rol de staff o de otro tenant recibe `403` en cualquier endpoint del contrato C.
  - Una imagen de origen, un photoshoot o un `GenerationJob` que pertenece a otro `product_link` no es accesible ni referenciable desde este producto.
  - Falsificar un identificador externo no habilita generar ni publicar: la propiedad se lee exclusivamente de `ProductLink` persistido.
- **Related Stories**: transversal a todas las historias; verificado explícitamente en `003-source-image-rejection` y en las historias de la unidad de aprovisionamiento.

### FR-16: Catálogo de opciones del photoshoot
- **Descripción**: BFashion necesita descubrir, antes de mostrar el formulario del staff, qué plantillas, modelos, poses y valores de `cloth_type` existen de verdad en Virtual Closet — exactamente los campos que `FR-5` acepta como entrada (`template_id`, `model_ids`, `pose_ids`/`pose_count`, `cloth_type`, `background`, `colors`). Sin esto, el formulario tendría que llevar esas opciones incrustadas a mano y se desincronizaría en cuanto alguien creara una plantilla nueva o diera de alta un modelo. **Hueco detectado por el agente del intent hermano `020-ai-product-imagery-integration` como su pregunta abierta OQ-3, con dueño «Intent 009»; se cierra aquí.**
- **Contrato**: `GET /api/integration/v1/products/{external_product_id}/photoshoot-options`. Salida: `templates[]` (`id`, `name`, `scope`, `wholesaler_scope`, `version`, `model`, `background`, `colors`, `rack`, `updated_at`), `models[]` (`id`, `name`, `available_poses`, `preview_url`), `cloth_types[]` (conjunto cerrado con etiqueta), `background_suggestions[]` y `color_suggestions[]` (valores distintos usados por plantillas activas, explícitamente no exhaustivos), `max_pose_count`, `catalog_version`.
- **Decisión de diseño — un único endpoint agregado, no uno por recurso**: el consumidor real es una sola pantalla del staff. Fragmentar en `GET .../templates`, `GET .../models`, `GET .../cloth-types` obligaría a BFashion a hacer 3-4 round trips para poblar un formulario que se abre a menudo, y multiplicaría la superficie de contrato a mantener entre ambos intents. Un endpoint agregado mantiene el contrato compacto y es coherente con `GET .../photoshoots/{id}` (FR-8), que ya agrega estado y candidatos en una sola respuesta por la misma razón.
- **Decisión de diseño — `cloth_type` es un catálogo cerrado; `background` y `colors` no lo son**: `cloth_type` tiene un enum cerrado y verificado en código (`upper_body | lower_body | dress`, ver `models/batch_job.py`, `api/schemas/pose_sets.py`), así que se expone como catálogo autoritativo. `background` y `colors` son campos generativos de texto libre / JSONB en `ImageTemplate` — FR-4 ya establece que «modelo, fondo y percheros son instrucciones/referencias generativas, no posiciones exactas garantizadas». Inventar un enum cerrado para ellos sería falso de cara al dominio; en su lugar se exponen como **sugerencias no exhaustivas** derivadas de los valores realmente usados por plantillas activas, para poblar un autocompletar sin fingir que son las únicas opciones válidas.
- **Aceptación**:
  - Solo se listan plantillas en `status: active`; las `draft` y `archived` no aparecen, coherente con FR-3 del intent 008 (archivar impide seleccionar).
  - `templates[]` respeta el alcance del mayorista del vínculo: las plantillas `common` siempre aparecen; las `private` solo si pertenecen al mayorista del `product_link` resuelto.
  - `models[]` solo incluye modelos del mayorista del vínculo (`Model.mayorista_id`), con sus poses realmente disponibles (subconjunto de `front | side | back` con foto cargada), no las tres por defecto.
  - `max_pose_count` refleja el límite real del dominio (3, `VALID_POSES` en `services/model_pose_service.py`), para que BFashion valide `pose_count` en su propio formulario antes de disparar el photoshoot.
  - La consulta es de solo lectura: no requiere `staff_id` ni `authorize_staff`, siguiendo el mismo patrón ya establecido por los `GET` existentes del contrato B (`get_product_generation_job`, `list_product_publication_candidates`), que solo resuelven el vínculo y no autorizan staff. Sí exige `X-Service-Id`/`X-Service-Secret` y resolución fail-closed del vínculo.
  - Un vínculo inexistente, inactivo o de otro tenant responde `404`/`403` sin filtrar catálogo.
  - `catalog_version` cambia cuando cambia cualquier plantilla activa o modelo del mayorista, para que BFashion pueda decidir si refresca su copia en caché sin comparar campo a campo. Se admite `ETag`/`If-None-Match` con `304` como mecanismo, a definir en la etapa de diseño técnico del bolt.
  - La respuesta no contiene el `prompt` completo de plantillas privadas de otro mayorista, ni credenciales, ni claves de almacenamiento crudas.
- **Related Stories**: `001-photoshoot-options-catalog`, `002-catalog-isolation-and-freshness`

---

## Non-Functional Requirements

Todos los requisitos no funcionales tienen prioridad **Must** salvo indicación contraria. Los valores numéricos son propuestas para aprobación.

### NFR-1: Latencia de las rutas servidor-a-servidor y cadencia de polling
- **Métrica y criterio**: Con 10 llamadas concurrentes del servicio de BFashion, `product-links`, `staff-identities`, `source-images:presign`, `source-images:confirm`, `photoshoot-options`, el disparo de photoshoot y la consulta de estado agregado tienen p95 ≤ 1 s, excluyendo la transferencia del archivo y el tiempo de inferencia. El disparo responde `202` sin esperar a ninguna etapa. La consulta de estado agregado y la de catálogo no disparan llamadas al proveedor. Se documenta una cadencia de polling recomendada acorde a latencias de minutos (propuesta: 5 s, con respaldo exponencial hasta 30 s). `photoshoot-options` se espera consultado con más frecuencia (cada apertura de pantalla del staff), por lo que admite `ETag`/`304` para evitar recomputar el catálogo en cada llamada.

### NFR-2: Tope global de concurrencia contra el proveedor
- **Métrica y criterio**: Hoy no existe: `ConcurrencyGuardService` es un lease por job, no un límite global. Se introduce un tope configurable de llamadas simultáneas al proveedor por despliegue (propuesta: 2, coherente con NFR-1 del intent 008); el excedente queda en cola y no falla. Un photoshoot que expande a 12 resultados con el tope en 2 completa igualmente, con los 12 resultados, sin superar 2 llamadas simultáneas al proveedor en ningún instante medido. El tiempo en cola se expone por separado del tiempo de ejecución en el estado agregado.

### NFR-3: Tiempos de espera acordes a Replicate
- **Métrica y criterio**: `_REQUEST_TIMEOUT_SECONDS = 60` en `services/image_generation_providers.py` no sirve para latencias de minutos. El timeout por llamada pasa a ser configurable por proveedor, con valor de partida ≥ 900 s para Replicate; `TRYOFF_MODEL_TIMEOUT_SECONDS` (1800 s) es el precedente en este repositorio. Al vencer, el estado de fallo se refleja en ≤ 30 s. Un timeout con resultado desconocido **no** se reintenta automáticamente: requiere reintento explícito, como ya hace `RetryPolicyService`. Los `429` se reintentan como máximo 2 veces respetando `Retry-After`. Los errores no transitorios no se reintentan.

### NFR-4: Contabilidad de uso con forma de Replicate
- **Métrica y criterio**: `UsageAccountingService` filtra hoy a `total_tokens`, `input_tokens`, `output_tokens` y sus detalles, de modo que Replicate quedaría siempre como `unknown`. Se amplía la normalización para aceptar la forma que Replicate sí reporta (identificador de predicción, tiempo de predicción, métricas), conservando la regla existente: lo que el proveedor no informa se registra como `unknown`, **nunca** como cero. Tras ejecutar un photoshoot real contra Replicate, al menos un `provider_invocation` queda con `usage_status = "reported"` y su modelo identificado. Cualquier coste calculado se identifica como estimación.

### NFR-5: Durabilidad e integridad del resultado
- **Métrica y criterio**: Reiniciar servicios conserva photoshoots, etapas, resultados, selección, configuración y estado de sincronización. Un resultado no se marca completado hasta persistir su archivo; un destino no se marca `synced` hasta confirmar imagen y configuración. Se conservan referencias duraderas de almacenamiento, no solo URLs temporales: una `transfer_url` caducada se puede volver a emitir desde el `storage_key` sin regenerar la imagen. Un fallo de sincronización con BFashion nunca destruye ni oculta un resultado ya generado aquí.

### NFR-6: Aislamiento, credenciales y privacidad
- **Métrica y criterio**: Las pruebas verifican que un `ServiceClient` de un tenant no resuelve vínculos, imágenes de origen, photoshoots ni resultados de otro. Ninguna credencial de proveedor (OpenAI, Replicate) ni de almacenamiento aparece en respuestas HTTP ni en registros; el navegador del staff solo recibe una URL presignada de subida acotada a una clave y una operación. Falsificar `staff_id`, `external_product_id` o `external_wholesaler_id` no habilita generar ni publicar. Los resultados privados de un mayorista no se vuelven públicos por una sincronización fallida.

### NFR-7: Verificabilidad visual y del overlay
- **Métrica y criterio**: La validación previa a entrega incluye al menos 4 photoshoots reales contra Replicate: 2 desde `garment_on_model` y 2 desde `flat_garment`, cubriendo prenda superior, inferior y vestido. El staff registra aceptación o rechazo según conservación de color, silueta, estampado e identidad del modelo. Cada tipo de entrada aporta al menos un resultado aceptado. Los casos de overlay usan slugs reales de BFashion, incluido al menos uno de más de 30 caracteres, y se verifica que el texto queda completo y dentro de la imagen, o bien que la versión queda `blocked` con motivo medido. No se promete fidelidad automática de todos los resultados.

---

## Constraints

### Technical Constraints

**Estándares del proyecto**: el Construction Agent carga los estándares desde `memory-bank/standards/`. Aquí solo se listan las restricciones propias de este intent.

- Capas obligatorias: `api/routers → services → repositories → models` (`backend/AGENTS.md`). El orquestador vive en `services/`, no en el router ni en la task.
- Cualquier cambio en `backend/models/` exige una revisión de Alembic en `backend/alembic/versions/`. Nada de tocar el esquema a mano.
- Solo un tenant en juego, pero el aislamiento existente por `tenant_id` no se relaja en ninguna consulta nueva.
- El contrato A (`PUT /internal/v1/products/{id}/images`) no se modifica en este intent.
- El contrato B (6 endpoints ya existentes) no se modifica en este intent.
- Los pipelines cookie-auth existentes (`/api/tryoff`, `/api/vton`, `/api/batches`, `/api/pose-sets`, `/api/composition`) siguen funcionando igual: el orquestador los consume, no los sustituye.
- Sin camino de subida multipart por el puente: solo presign + confirm.
- Sin interfaz nueva en el frontend de Virtual Closet.

### Business Constraints

- Solo la selección explícita del staff publica. Nunca publicación automática.
- El consumo de proveedores se centraliza en la cuenta de la plataforma; no hay claves por mayorista ni facturación automática en este intent.
- El intent hermano `020-ai-product-imagery-integration` avanza en paralelo contra el mismo contrato compartido: los cambios de contrato se anuncian, no se aplican en silencio.

---

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| El navegador del staff de BFashion alcanza el endpoint público de MinIO/S3 de Virtual Closet | La subida directa falla y no hay camino alternativo en código | Decisión explícita del dueño del producto: se trata como problema de despliegue. Verificar el endpoint público y CORS antes del primer bolt de subida |
| `pose_set` + `batch_job` cubren la expansión a N poses sin cambios de contrato interno | El orquestador tendría que reimplementar la expansión de poses | Se verifica en la etapa de modelo del bolt de orquestación; `PoseSet` ya es `UNIQUE(batch_id)` y agrupa modelo×prenda×poses |
| Un slug de producto típico cabe en una línea con la configuración de overlay por defecto | Muchas `CompositionVersion` quedarían `blocked` y la galería llegaría sin overlay | FR-11 hace el fallo explícito y no destructivo; **OQ-1** escala la política de ajuste al dueño del producto |
| El `Mayorista` espejo con rol `staff` satisface `_authorize_staff` sin modificarlo | Habría que tocar la autorización del puente ya entregada | Se valida en la primera historia de aprovisionamiento, contra `integration_service.STAFF_ROLES` |
| Replicate acepta la carga de un photoshoot expandido dentro del tope de concurrencia | Colas largas y expiración de expectativas del staff | NFR-2 y NFR-3 fijan tope, cola y timeouts medibles; el estado agregado expone el tiempo en cola |

---

## Open Questions

| ID | Question | Owner | Resolution |
|----|----------|-------|------------|
| OQ-1 | BFashion estampa el **slug** del producto (`blusa-manga-globo`), no un SKU corto. `sku_renderer.evaluate_fit` mide **una sola línea** con `ImageFont.load_default` y marca `blocked` si no cabe. ¿Qué hacemos con slugs largos: (a) dejarlos `blocked` y que el staff ajuste tamaño o posición, (b) permitir ajuste automático del tamaño de fuente dentro de un mínimo legible, o (c) permitir partir en dos líneas? | Dueño del producto | **Pendiente.** V1 asume (a): fallo explícito y no destructivo, según FR-11. (b) y (c) cambian `spec_hash` y la semántica determinista de ADR-054 |
| OQ-2 | Los dos endpoints de `staff-identities` **no estaban** en la propuesta de contrato C del brief. Su forma está fijada en FR-2 porque el comando `manage.py link_staff_identity` del intent hermano los va a consumir. ¿Se confirma la forma exacta (`external_staff_id` como string, idempotencia por `(system, external_staff_id)`, revocación por `:revoke`)? | Dueño del producto + intent 020 | **Pendiente de confirmación cruzada con el intent hermano** |
| OQ-3 | ¿Qué valor toma el tope global de concurrencia contra Replicate en producción? La propuesta es 2, heredada de NFR-1 del intent 008, pero ese valor se fijó pensando en OpenAI | Dueño del producto | Propuesta NFR-2: 2, configurable. Ajustable sin cambio de diseño |
| OQ-4 | ¿Cuántas poses por defecto genera un photoshoot cuando BFashion no especifica `pose_ids`? Afecta a `expected_results`, al coste por producto y al tiempo de cola | Dueño del producto | Propuesta: 3 poses, coherente con `Model` (1..3 fotos de pose). Configurable |
| OQ-5 | ¿El `Mayorista` espejo de un staff consume cuota o límites mensuales del tenant (`LimiteMensualAlcanzadoError` en `prenda_service`)? Si sí, el aprovisionamiento masivo de staff podría agotar límites pensados para mayoristas reales | Diseño de unidades | A resolver en la unidad de aprovisionamiento; propuesta: los espejos no computan cuota de mayorista |

---

## Out of Scope

- Cualquier cambio en el lado BFashion: lo cubre el intent hermano `020-ai-product-imagery-integration`.
- Implementación de variantes de color: V1 solo deja el asiento reservado (FR-14).
- Multi-tenancy más allá del aislamiento ya existente.
- Interfaz nueva en el frontend de Virtual Closet.
- Camino de subida multipart por el puente.
- Migración de los flujos cookie-auth existentes al puente.
- Sustitución de OpenAI por Replicate en los modos `text`, `edit` y `extraction` del intent 008.
- Facturación o cuotas comerciales por uso de proveedor.

---

## Estado de revisión

- Checkpoint 1: resuelto. Las cuatro decisiones (orquestación, identidad de staff, subida, interfaz) las fijó el dueño del producto.
- Checkpoint 2: los 16 FR, 7 NFR y las preguntas abiertas se elaboraron y llevaron a contexto, unidades, historias y bolts sin una revisión de aprobación separada; quedaron sujetos a la revisión conjunta de Checkpoint 3.
- Checkpoint 3, primera pasada: reveló un hueco real (FR-16, catálogo de opciones del photoshoot), detectado por el agente del intent hermano contra este mismo contrato. Incorporado antes de cerrar Checkpoint 3.
- Checkpoint 3, segunda pasada: **aprobado por el dueño del producto el 2026-09-18**, con el catálogo ya incorporado.
- Checkpoint 4: inception cerrada. Intent listo para Construction, iniciando por el bolt `050-bridge-provisioning`.

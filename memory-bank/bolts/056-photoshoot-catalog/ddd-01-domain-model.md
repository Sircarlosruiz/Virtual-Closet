---
unit: 005-photoshoot-catalog
bolt: 056-photoshoot-catalog
stage: model
status: complete
updated: 2026-09-19T01:35:20Z
---

# Static Model: photoshoot-catalog

## Bounded Context

**Catálogo de opciones del photoshoot** (Photoshoot Options Catalog).

Este contexto es una **consulta de solo lectura** del puente BFashion ↔ Virtual Closet. Responde *qué puede elegir el staff* antes de disparar un photoshoot: plantillas seleccionables, modelos con poses reales y el conjunto cerrado de `cloth_type`.

No es dueño de ninguna entidad persistida. Compone un modelo de lectura a partir de tres contextos vecinos, siempre después de resolver el `ProductLink` activo del `ServiceClient`.

**Dentro del contexto**
- Agregar el catálogo visible para un producto vinculado
- Filtrar plantillas por visibilidad (`common` + `private` del dueño del vínculo) y por `status: active`
- Listar modelos del dueño del vínculo con las poses que realmente tienen foto
- Exponer el catálogo cerrado de `ClothType` y el tope de poses
- Derivar sugerencias no autoritativas de `background` y `colors`
- Derivar una `CatalogVersion` que cambie cuando cambie el material visible
- Fallar cerrado si el vínculo no es visible para el cliente

**Fuera del contexto**
- Crear, editar o archivar plantillas, modelos o poses (cookie-auth / staff de Virtual Closet)
- Disparar o orquestar photoshoots (`003-photoshoot-orchestration`)
- Autorizar `staff_id` (`resolve_staff_identity`, ADR-057): este GET no aserta staff
- Inventar un enum cerrado de `background` / `colors`
- Caché distribuida, CDN, webhooks de invalidación o paginación
- Cualquier escritura, cola Celery o llamada a proveedor de IA

Contextos vecinos: **Aprovisionamiento del puente** (`ProductLink`, `ServiceClient`), **Ciclo de vida de plantillas** (`ImageTemplate`), **Modelos y poses** (`Model`, `ModelPhoto`).

## Confirmación de persistencia

**Este bolt no introduce modelo de datos nuevo ni revisión Alembic.**

No hay tablas, columnas, índices, enums de BD ni migraciones. `CatalogVersion` no se almacena: se deriva en cada consulta. `ClothType` y `MaxPoseCount` son constantes de aplicación. El `ETag` HTTP se calcula en presentación a partir de `CatalogVersion`; no es un concepto persistido.

## Domain Entities

Esta unidad **no crea entidades**. Lee raíces ya modeladas:

| Entity | Origen | Properties usadas | Business Rules en esta consulta |
|--------|--------|-------------------|----------------------------------|
| **ProductLink** (existente, no se muta) | 050 / contrato B | `system`, `external_product_id`, `external_wholesaler_id?`, `mayorista_id`, `tenant_id`, `is_active` | Única autoridad de propiedad. `system` y `tenant_id` salen del `ServiceClient`. Un vínculo inexistente, inactivo o de otro tenant no revela catálogo. `mayorista_id` es el dueño del alcance (ADR-060: espejo de staff que creó el vínculo, no una empresa). |
| **ServiceClient** (existente, actor) | Tenancy / Auth | `id`, `system`, `tenant_id`, `is_active` | Credenciales ausentes o inválidas, cliente o tenant inactivo → no autenticado. No se evalúa ningún dato de catálogo. |
| **ImageTemplate** (existente, no se muta) | 045 | `id`, `scope`, `wholesaler_id`, `version`, `status`, `name`, `model`, `background`, `colors`, `rack`, `updated_at` | Solo `status = active`. `common` siempre visible. `private` solo si `wholesaler_id` = `ProductLink.mayorista_id`. `draft` y `archived` nunca aparecen. No se expone `prompt` ni claves de almacenamiento. |
| **Model** (existente, no se muta) | 028 | `id`, `mayorista_id`, `name` | Solo modelos con `mayorista_id` = `ProductLink.mayorista_id`. Un modelo sin poses sigue listándose (`available_poses` vacío). |
| **ModelPhoto** (existente, no se muta) | 028 / 039 | `model_id`, `pose`, `minio_key` | Solo fotos con `model_id` y `pose` informados. Aporta el subconjunto real de `PoseType` y, si existe, la clave para una URL de previsualización. Fotos curadas (`model_id` nulo) están fuera. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| **PhotoshootOptionsCatalog** | `templates`, `models`, `cloth_types`, `background_suggestions`, `color_suggestions`, `max_pose_count`, `catalog_version` | Modelo de lectura inmutable. Igualdad por valor. Un catálogo vacío de privadas/modelos sigue siendo un catálogo válido. |
| **SelectableTemplate** | `id`, `name`, `scope`, `wholesaler_scope`, `version`, `model`, `background`, `colors`, `rack`, `updated_at` | Proyección de una `ImageTemplate` `active` visible. `wholesaler_scope` es el `wholesaler_id` si `private`, nulo si `common`. Nunca incluye `prompt` ni `storage_key`. |
| **CatalogModel** | `id`, `name`, `available_poses`, `preview_url?` | `available_poses` ⊆ `{front, side, back}` y solo las poses con foto. Orden canónico: `front`, `side`, `back`. `preview_url` es un `PresignedUrl` opcional, nunca una clave cruda. |
| **ClothType** | `upper_body` \| `lower_body` \| `dress` | Conjunto cerrado y autoritativo. El mismo que valida el disparo (FR-5). No se consulta a BD. |
| **PoseType** | `front` \| `side` \| `back` | Conjunto cerrado (028). Define el orden de `available_poses`. |
| **MaxPoseCount** | entero = `3` | Cardinalidad de `PoseType`. BFashion valida `pose_count` contra este tope. |
| **SuggestionSet** | lista de strings distintos | **No es un catálogo cerrado.** Unión de valores no nulos usados por plantillas *activas y visibles*. Un `colors` nulo no aporta nada. BFashion puede enviar un valor que no esté aquí. |
| **CatalogVersion** | token opaco derivado | Cambia si cambia cualquier plantilla activa visible o cualquier modelo del dueño del vínculo (alta, edición, archivo, nueva pose). No es un contador persistido. Dos consultas sin cambios producen el mismo valor. |
| **PresignedUrl** | `url`, `expires_at` | TTL existente de media (~15 min). Regenerada en cada lectura. Nunca se persiste ni se registra (NFR-6). |
| **ExternalProductId** | texto | Identifica el producto en BFashion. No implica propiedad. |
| **ExternalWholesalerId** | texto opcional | Si el vínculo lo tiene, un valor distinto en resolve falla cerrado (regla de 050). No selecciona otro dueño. |

## Aggregates

No hay raíz nueva. El objeto que viaja al consumidor es un **read model**, no un agregado persistido.

| Aggregate Root (leída) | Members usados | Invariants aplicados aquí |
|------------------------|----------------|---------------------------|
| **ProductLink** | — | (1) Visible solo si `is_active` y `tenant_id`/`system` del `ServiceClient`. (2) `mayorista_id` fija el alcance de privadas y modelos. (3) Resolve ocurre *antes* de tocar plantillas o modelos. |
| **ImageTemplate** | campos de composición, no `TemplateReference` | (1) `private` exige `wholesaler_id`; `common` no. (2) Solo `active` es listable en este catálogo — más estricto que `list_selectable` de 045, que aún admite `draft` para administración. (3) Visibilidad de alcance se aplica en servicio (ADR-051), no con un listener ORM nuevo. |
| **Model** | `ModelPhoto` con pose (0..3) | (1) Todas las fotos miembro comparten el `mayorista_id` de la raíz. (2) Como máximo una foto por `PoseType`. (3) Cero poses es un estado válido y observable. |

## Domain Events

Esta unidad **no emite eventos**. Es una consulta. Los cambios que invalidan `CatalogVersion` ya existen en los contextos dueños:

| Evento vecino | Efecto sobre este catálogo |
|---------------|----------------------------|
| `TemplateCreated` / `TemplateRevised` / `TemplateArchived` (045) | Si la plantilla queda (o deja de estar) `active` y visible, `CatalogVersion` cambia y las sugerencias pueden cambiar |
| `ModelCreated` / `PosePhotoUploaded` (028) | Si el modelo pertenece al dueño del vínculo, entra o cambia en `models[]` y `CatalogVersion` cambia |

V1 no escucha estos eventos: la siguiente consulta recalcula. No hay bus ni webhook hacia BFashion.

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| **PhotoshootCatalogService** (nuevo, solo lectura) | `get_photoshoot_options(client, external_product_id, external_wholesaler_id?) → PhotoshootOptionsCatalog` | Resolución fail-closed de `ProductLink`; lectura de plantillas seleccionables; lectura de modelos + poses del dueño |
| **ServiceAuthentication** (existente, no se modifica) | Verifica `X-Service-Id` / `X-Service-Secret` y entrega el `ServiceClient` | `ServiceClientRepository` |

Reglas de servicio:

1. **Autenticación primero.** Sin `ServiceClient` válido no se resuelve vínculo ni se lee catálogo.
2. **Vínculo segundo.** `get_photoshoot_options` exige un `ProductLink` activo del mismo `system`/`tenant_id`. Si el vínculo trae `external_wholesaler_id`, el valor asertado debe coincidir. Fallo → rechazo sin listar plantillas ni modelos.
3. **Sin `staff_id`.** Este GET no llama a `resolve_staff_identity` ni a `_authorize_staff`. Sigue el precedente de los GET del contrato B. ADR-057 aplica a *comandos* del contrato C que asertan staff, no a esta consulta.
4. **Dueño = `ProductLink.mayorista_id`.** Es el espejo de staff que creó el vínculo (ADR-060). Plantillas privadas y modelos de *otro* espejo del mismo tenant comercial no aparecen. Eso puede dejar el catálogo “vacío de propias” para un staff B que no creó el vínculo; no se ensancha el dueño en este bolt.
5. **Plantillas.** Unión de `common` + `private` del dueño, filtrada a `active`. El filtro de alcance vive en este servicio (o reutiliza `list_selectable` ya acotado). No se añade listener ORM (ADR-051).
6. **Modelos.** Solo `Model.mayorista_id = ProductLink.mayorista_id`. `available_poses` se deriva de fotos reales, nunca se rellena a las tres por defecto.
7. **`cloth_types` y `max_pose_count`.** Constantes. Van en la misma respuesta para que BFashion no las hardcodee.
8. **Sugerencias.** Distintos de `background` / `colors` no nulos de las plantillas *ya incluidas*. Se etiquetan como sugerencias, no como enum.
9. **`CatalogVersion`.** Agregado barato y determinista (p. ej. máximo `updated_at` / identidad+versión de plantillas visibles y modelos del dueño, o un hash de esos identificadores). Sin tabla de contador. El token HTTP (`ETag`) es un detalle de Stage 2.
10. **Vacío no es error.** Mayorista sin privadas ni modelos: `templates[]` puede traer solo `common`, `models[]` vacío, `200`.
11. **Cero escrituras.** Ningún `save`, enqueue ni llamada a proveedor.

## Repository Interfaces

No se introduce repositorio nuevo. Se reutilizan contratos existentes:

| Repository | Entity | Methods usados (solo lectura) |
|------------|--------|-------------------------------|
| **ProductLinkRepository** (existente) | `ProductLink` | Resolución fail-closed ya entregada (`resolve_active_link` / equivalente). No se extiende el esquema. |
| **ImageTemplateRepository** (existente) | `ImageTemplate` | Listado de plantillas seleccionables por alcance (`common` ∪ `private` del mayorista). Este servicio exige además `status = active`. |
| **ModelRepo** (existente) | `Model` | Listar modelos por `mayorista_id`. |
| **ModelPhotoRepo** (existente) | `ModelPhoto` | Listar poses por modelo (orden `front`, `side`, `back`). |

Si falta un método de listado por mayorista, Stage 2 lo añade al repositorio existente. Eso no es modelo de datos nuevo.

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Catálogo de opciones / photoshoot-options** | Única respuesta agregada con plantillas, modelos, `cloth_types`, sugerencias, `max_pose_count` y `catalog_version`. |
| **Dueño del vínculo** | `ProductLink.mayorista_id`. En V1 es el espejo de staff que creó el vínculo, no una empresa (ADR-060). |
| **Plantilla seleccionable** | `ImageTemplate` con `status = active` y alcance visible: `common` o `private` del dueño. |
| **Plantilla común** | Visible para cualquier vínculo del tenant. |
| **Plantilla privada** | Visible solo si `wholesaler_id` = dueño del vínculo. Nunca se filtra la de otro mayorista. |
| **Pose disponible** | `PoseType` de un modelo que tiene foto cargada. No es el enum completo. |
| **Cloth type** | Categoría de prenda para inferencia. Catálogo cerrado: `upper_body`, `lower_body`, `dress`. |
| **Sugerencia** | Valor de `background` o `color` observado en plantillas activas visibles. No autoriza ni restringe el disparo. |
| **Catalog version** | Señal opaca de frescura del catálogo visible. Cambia cuando cambia el material; no es un id de fila. |
| **Fail-closed** | Ante duda (credencial, tenant, vínculo) se rechaza y no se lee catálogo. No se filtra existencia a un cliente no autenticado o de otro tenant. |
| **Contrato C (lectura)** | Este GET vive bajo `/api/integration/v1` y autentica servicio, pero no aserta `staff_id`. |

## Decisiones de dominio que condicionan el diseño

1. **Sin persistencia nueva.** Confirmado: cero tablas, cero Alembic. Cualquier tentación de “tabla de versión de catálogo” se rechaza; `CatalogVersion` se deriva.
2. **Un solo recurso agregado.** El consumidor es una pantalla. Fragmentar en templates/models/cloth-types multiplicaría round trips y superficie (FR-16).
3. **`cloth_type` es cerrado; `background`/`colors` no.** Inventar un enum de fondo o color mentiría al dominio (FR-4 / FR-16).
4. **Alcance por espejo, no por empresa.** ADR-060. Dos staff de la misma org BFashion no comparten automáticamente privadas ni modelos. Se documenta; no se “arregla” ensanchando `mayorista_id`.
5. **Catálogo más estricto que la admin de plantillas.** 045 permite ver `draft` en administración. Este catálogo solo muestra `active`.
6. **Sin staff en la consulta.** ADR-057 no se invoca. Un espejo revocado no impide leer el catálogo de un vínculo que sigue activo; el bloqueo de *disparo* es de otra unidad.
7. **Aislamiento de plantillas en servicio.** ADR-051. No se extiende el listener de ADR-012 a `wholesaler_id`. El tenant sí sigue ADR-012 vía `ServiceClient` + resolve del vínculo.
8. **Taxonomía de rechazo** (HTTP exacto en Stage 2; aquí el significado):
   - Cliente ausente/inválido → no autenticado; no se toca el catálogo
   - Vínculo inexistente, inactivo o de otro tenant → no encontrado en el alcance del cliente; **sin filtrar existencia** (espíritu ADR-040). Las historias admiten `403`/`404`; el default de dominio es “no visible”, no “existe pero no es tuyo”
   - `If-None-Match` desconocido → se trata como ausencia de condicional; se devuelve el catálogo completo (detalle HTTP en Stage 2)
9. **Lista acotada, sin paginación.** Excepción consciente a la convención de listas paginadas: V1 asume catálogo pequeño por mayorista. No se introduce `page`/`page_size`.
10. **Sin secreto ni clave cruda.** Ni `prompt` de ajenas, ni `minio_key`, ni secretos de servicio. `preview_url` es presignada y de corta vida.

## Invariants

1. Cero mutaciones de estado en este contexto.
2. Ningún dato de otro tenant es alcanzable.
3. Ninguna plantilla `draft` o `archived` aparece.
4. Ninguna plantilla `private` de otro `wholesaler_id` aparece, aunque comparta tenant.
5. `models[]` no incluye modelos de otro `mayorista_id`.
6. `available_poses` nunca inventa poses sin foto.
7. `cloth_types` es exactamente `{upper_body, lower_body, dress}`.
8. `max_pose_count` es exactamente `3`.
9. `background_suggestions` y `color_suggestions` no se presentan como enum cerrado.
10. `CatalogVersion` es estable si el material visible no cambió, y distinta si cambió una plantilla activa visible o un modelo del dueño.
11. Resolve del vínculo precede a cualquier lectura de catálogo.

## Stories Covered

| Story | Cubierta por |
|-------|----------------|
| **001-photoshoot-options-catalog** | `PhotoshootCatalogService.get_photoshoot_options`; VOs `PhotoshootOptionsCatalog`, `SelectableTemplate`, `CatalogModel`, `ClothType`, `SuggestionSet`, `MaxPoseCount`; invariantes 3–9; vacío válido |
| **002-catalog-isolation-and-freshness** | Resolve fail-closed de `ProductLink`; `ServiceAuthentication` primero; `CatalogVersion`; taxonomía de rechazo; invariantes 1, 2, 10, 11 |

## Prior Decisions Applied

- **ADR-060**: el alcance de privadas y modelos es `ProductLink.mayorista_id` (espejo). No se introduce mayorista-empresa.
- **ADR-057**: no se usa. Este GET no aserta `staff_id`.
- **ADR-051**: visibilidad `common`/`private` en la capa de servicio, sin listener ORM nuevo.
- **ADR-040**: no filtrar existencia de vínculo o producto ajeno; default de dominio = no visible.
- **ADR-012**: `tenant_id` siempre del `ServiceClient`; el isolate del puente no se relaja.
- **ADR-015**: no se añade RLS para esta consulta.

## Story Acceptance Mapping

### 001-photoshoot-options-catalog

- Vínculo activo → catálogo con `templates[]`, `models[]`, `cloth_types[]`, sugerencias, `max_pose_count`, `catalog_version`
- `draft`/`archived` ausentes
- `common` siempre presente
- `private` ajena ausente
- Poses reales, no las tres por defecto
- `cloth_types` = conjunto cerrado
- `max_pose_count` = 3
- Sugerencias explícitamente no cerradas

### 002-catalog-isolation-and-freshness

- Cliente de otro tenant → rechazo sin filtrar catálogo
- Vínculo inactivo → no visible
- Misma versión + condicional fresco → no hace falta retransferir el cuerpo (mecanismo HTTP en Stage 2)
- Cambio de plantilla activa o alta de modelo → `CatalogVersion` distinta
- Credenciales inválidas → no autenticado, sin evaluar catálogo

---
unit: 005-photoshoot-catalog
bolt: 056-photoshoot-catalog
stage: design
status: complete
updated: 2026-09-19T01:36:51Z
---

# Technical Design - photoshoot-catalog

## Architecture Pattern

**Layered DDD dentro del monolito FastAPI** (`api/routers → services → repositories → models`).

No hay bounded context hexagonal nuevo ni router paralelo. El puente S2S ya vive en `integration`. Este bolt **añade un GET de agregación** a esa superficie y un servicio de solo lectura.

Razones:

- `get_service_client` ya es el borde de autenticación del contrato B y C.
- `ProductLinkService.resolve_active_link` ya es la autoridad de visibilidad del producto. No se reimplementa.
- Plantillas y modelos ya tienen repositorios (045, 028). Se reutilizan; no se copian reglas a un ORM listener (ADR-051).
- Cero persistencia nueva: no hay agregado que justificaría un módulo de modelos.

## Layer Structure

```text
┌─────────────────────────────────────────────────────────────┐
│ Presentation                                                │
│   api/routers/integration.py     + GET photoshoot-options   │
│   api/schemas/integration.py     + DTOs de catálogo         │
├─────────────────────────────────────────────────────────────┤
│ Application                                                 │
│   services/photoshoot_catalog_service.py   NUEVO (lectura)  │
│   services/product_link_service.py         resolve (sin     │
│                                            cambios de       │
│                                            contrato)        │
├─────────────────────────────────────────────────────────────┤
│ Domain                                                      │
│   read model en memoria (PhotoshootOptionsCatalog)          │
│   constantes ClothType / VALID_POSES (existentes)           │
│   excepciones de visibilidad en services/                   │
├─────────────────────────────────────────────────────────────┤
│ Infrastructure                                              │
│   repositories/image_template_repo.py    reutilizado        │
│   repositories/model_repo.py             + listado si falta │
│   repositories/model_photo_repo.py       reutilizado        │
│   presign de media existente             preview_url        │
│   (sin Alembic)                                             │
└─────────────────────────────────────────────────────────────┘
```

Responsabilidades por capa:

- **Router**: `Depends(get_service_client)`, lee `If-None-Match`, traduce excepciones → HTTP, escribe `ETag` / `304`. No agrega catálogo.
- **Service**: resolve → carga → filtra `active` / alcance → deriva sugerencias y `catalog_version` → (si no es 304) pide presigns.
- **Repository**: listados por alcance. Sin reglas de negocio.
- **Schema**: forma del JSON. No declara `system` ni `tenant_id`.

## Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Service | `services/photoshoot_catalog_service.py` | `get_photoshoot_options` — única orquestación de este bolt |
| Service | `services/product_link_service.py` | Solo `resolve_active_link` (o equivalente). Sin cambios de contrato |
| Schema | `api/schemas/integration.py` | `PhotoshootOptionsResponse` y submodelos |
| Router | `api/routers/integration.py` | `GET .../photoshoot-options` |
| Auth | `core/dependencies.py` `get_service_client` | Reutilizado, sin cambios |
| Repo | `repositories/image_template_repo.py` | `list_selectable(wholesaler_id)` existente |
| Repo | `repositories/model_repo.py` | `list_by_mayorista(mayorista_id)` — añadir si no existe |
| Repo | `repositories/model_photo_repo.py` | `list_by_model` existente |
| Media | helper de URL presignada existente | Solo tras decidir que la respuesta es `200` |
| Const | enum/`VALID_POSES` ya usados por pose-sets / batch_job | Importar; **no** crear una tercera copia |

`integration_service.py` no se edita. `StaffIdentityService` no se llama.

## API Design

Base: `/api/integration/v1`. Auth: `X-Service-Id` + `X-Service-Secret`. Sin cookie. Sin `staff_id`.

### GET `/api/integration/v1/products/{external_product_id}/photoshoot-options`

**Path**

- `external_product_id`: string 1..255

**Query**

- `external_wholesaler_id` (opcional): si el vínculo persistido lo tiene, debe coincidir o el resolve falla cerrado. No selecciona otro dueño (ADR-060).

**Headers (request)**

- `X-Service-Id`, `X-Service-Secret` (obligatorias)
- `If-None-Match` (opcional): uno o más ETags. Si alguno coincide con el ETag actual → `304`

**Headers (response 200)**

- `ETag: W/"<catalog_version>"`
- `Cache-Control: private, no-cache`

`private` evita caché compartida entre tenants. `no-cache` obliga a revalidar (el caso de uso es “cada apertura de pantalla”). No hay CDN ni caché de aplicación.

**Headers (response 304)**

- `ETag: W/"<catalog_version>"`
- sin cuerpo

**Response 200**

```json
{
  "templates": [
    {
      "id": "uuid",
      "name": "string",
      "scope": "common",
      "wholesaler_scope": null,
      "version": 1,
      "model": "string | null",
      "background": "string | null",
      "colors": null,
      "rack": "string | null",
      "updated_at": "2026-09-18T11:50:00Z"
    }
  ],
  "models": [
    {
      "id": "uuid",
      "name": "string",
      "available_poses": ["front", "side"],
      "preview_url": "https://... | null"
    }
  ],
  "cloth_types": [
    {"value": "upper_body", "label": "Upper body"},
    {"value": "lower_body", "label": "Lower body"},
    {"value": "dress", "label": "Dress"}
  ],
  "background_suggestions": ["studio white"],
  "color_suggestions": ["#111111"],
  "max_pose_count": 3,
  "catalog_version": "sha256:ab…32 hex chars…"
}
```

Notas de contrato:

- Los nombres `background_suggestions` y `color_suggestions` son la distinción explícita “no es un enum cerrado”. No se añade un wrapper `suggestion_policy`.
- `cloth_types` va como objetos `{value, label}` (FR-16: conjunto cerrado con etiqueta). `value` es lo que FR-5 acepta.
- `wholesaler_scope` = `ImageTemplate.wholesaler_id` si `scope=private`, `null` si `common`.
- `colors` en cada plantilla se pasa tal cual está persistido (string, lista o `null`). Las sugerencias sí se aplanan a strings.
- `available_poses` ⊆ `{front, side, back}`, orden canónico `front < side < back`. Nunca se rellena a tres por defecto.
- `preview_url`: presign de la primera pose existente en ese orden. Sin poses → `null`. Nunca `minio_key`.
- `catalog_version` en el cuerpo **es el mismo token** que va dentro del `ETag` (sin `W/` ni comillas).
- Sin paginación (excepción a la convención de listas): V1 asume catálogo acotado por mayorista.
- `extra = "ignore"` en request schemas si se añaden query models. El servicio no lee `system`/`tenant_id` del cliente.

**Orden de arrays (UX + tests estables)**

- `templates[]`: `common` primero, luego `private`; dentro de cada grupo, `name` asc, `id` asc.
- `models[]`: `name` asc, `id` asc.
- Sugerencias: orden lexicográfico, distintas, sin vacíos.

## Data Persistence

**Ninguna tabla nueva. Ninguna columna. Ninguna revisión Alembic.**

| Table | Uso | Escritura |
|-------|-----|-----------|
| `product_links` | Resolve fail-closed | No |
| `image_templates` | Listado seleccionable + filtro `active` | No |
| `models` | Listado por `mayorista_id` | No |
| `model_photos` | Poses reales y clave para presign | No |

`catalog_version` no se guarda. Se deriva en proceso.

Si `ModelRepo` no tiene listado por mayorista, se añade un `SELECT` con `mayorista_id = :id` (y el filtro de tenant que el listener ADR-012 ya aplique). Eso no es migración.

## CatalogVersion y ETag

### Por qué no `max(updated_at)` solo

Archivar o dejar de mostrar una plantilla puede **sacar** un id del conjunto visible. Si el `updated_at` máximo del resto no cambia, un `max()` mentiría: BFashion recibiría `304` con un catálogo ya incompleto. Una pose nueva tampoco está garantizada en `Model.updated_at` (028 modeló `created_at` en `Model` y `uploaded_at` en `ModelPhoto`).

### Algoritmo (determinista)

Tras tener el conjunto **ya filtrado** (plantillas `active` visibles + modelos del dueño + sus fotos de pose):

1. Construir un payload canónico (JSON UTF-8, keys ordenadas, sin espacios significativos):

```text
{
  "v": "photoshoot-options:v1",
  "templates": [
    {"id": "<uuid>", "version": 1, "updated_at": "<iso>", "scope": "common"}
  ],
  "models": [
    {
      "id": "<uuid>",
      "photos": [
        {"pose": "front", "photo_id": "<uuid>", "uploaded_at": "<iso>"}
      ]
    }
  ],
  "cloth_types": ["upper_body", "lower_body", "dress"],
  "max_pose_count": 3
}
```

   Arrays interiores ordenados por `id` / `pose`. `photos` solo con `model_id` y `pose` informados.

2. `catalog_version = "sha256:" + sha256(payload).hexdigest()[:32]`

3. `ETag = W/"<catalog_version>"`

El prefijo `photoshoot-options:v1` invalida cachés si más adelante cambia el conjunto cerrado o la forma del hash.

### Por qué ETag débil (`W/`)

`preview_url` se regenera en cada `200` y no entra en el hash. El cuerpo no es byte-idéntico entre dos `200` del mismo catálogo semántico. Un ETag fuerte mentiría.

### Comparación `If-None-Match`

1. Parsear la cabecera (uno o varios validators, con o sin `W/`, con o sin comillas).
2. Si **ningún** token coincide con `catalog_version` actual (incluido un valor desconocido) → tratar como ausente → `200` con cuerpo.
3. Si coincide → `304`, **sin** generar presigns y sin serializar el JSON.

Esto ahorra transferencia y firmas MinIO (la parte cara). Los reads de BD sí ocurren: V1 no tiene caché de versión. Cumple “no retransferir el catálogo completo” (historia 002) sin infraestructura nueva.

## Use-case flow

```text
1. Router: get_service_client
      ausente / inválido / cliente o tenant inactivo → 401
      (no se llama al servicio de catálogo)
2. Service.get_photoshoot_options(client, external_product_id, external_wholesaler_id?)
3. ProductLinkService.resolve_active_link(...)
      cualquier fallo de visibilidad → PhotoshootCatalogNotVisibleError
      (no se listan plantillas ni modelos)
4. asyncio.gather:
      - ImageTemplateRepository.list_selectable(wholesaler_id=link.mayorista_id)
      - ModelRepo.list_by_mayorista(link.mayorista_id)
5. Filtrar plantillas a status == active
   (list_selectable de 045 excluye archived pero puede incluir draft)
6. Cargar ModelPhoto por cada modelo (o un listado batch por ids)
   available_poses = poses reales, orden canónico
7. Derivar background_suggestions / color_suggestions
   CatalogVersion.hash(conjunto filtrado)
8. Router: si If-None-Match coincide → 304
9. Si 200: presign de preview por modelo (primera pose); armar DTO; ETag
```

Reglas:

- `list_selectable` recibe el **dueño del vínculo** (`ProductLink.mayorista_id`), no un id externo (ADR-060).
- El servicio vuelve a afirmar alcance: descarta `private` cuyo `wholesaler_id` ≠ dueño. Defensa en profundidad, no un listener nuevo (ADR-051).
- `colors` nulo o vacío no aporta sugerencias. Si `colors` es lista, cada string no vacío es un candidato; si es string, el string completo es un candidato.
- Vacío de privadas/modelos → `200`, no error.
- Cero `commit`, cero Celery, cero proveedor de IA.

## Security Design

| Concern | Approach |
|---------|----------|
| Autenticación de servicio | `get_service_client`; 401 idéntico si faltan cabeceras, secreto mal, cliente o tenant inactivo. No se evalúa catálogo |
| Autorización de staff | **No aplica.** Sin `staff_id`, sin `resolve_staff_identity`, sin `_authorize_staff`. Un espejo revocado no bloquea esta lectura; el disparo (053) sí |
| Visibilidad del producto | `resolve_active_link` + mapeo de **todo** fallo a 404 genérico en este GET |
| Tenant isolation | `system`/`tenant_id` solo del `ServiceClient`. Listener ADR-012 donde las tablas lo tengan. Filtros explícitos de `mayorista_id` / `wholesaler_id` |
| Alcance de plantillas | Servicio: `common` ∪ `private` del dueño; solo `active`. ADR-051 |
| Existencia (ADR-040) | 404 único para vínculo inexistente, inactivo, otro tenant o `external_wholesaler_id` distinto. Sin 403 que confirme que el producto existe |
| Secretos / claves | Sin `prompt`, sin `minio_key`, sin secretos de servicio. `preview_url` no se loguea (NFR-6) |
| Caché compartida | `Cache-Control: private, no-cache`. El ETag no se usa en un store multi-tenant |
| Input | Path 1..255; query opcional string; Pydantic |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| NFR-1 p95 ≤ 1 s / 10 concurrentes | Síncrono en request, 1 resolve + 2 listados en paralelo, hash in-process, presign solo en `200`. Sin I/O de proveedor |
| NFR-1 cadencia de refresco | `ETag` / `304` para no reenviar el JSON ni refirmar URLs si el material no cambió |
| NFR-6 aislamiento | Tests: otro tenant / vínculo inactivo / privadas ajenas / modelos ajenos; 401 sin tocar datos |
| Escalabilidad | Catálogo acotado por mayorista (V1). Sin paginación, sin Redis, sin tabla de versión |
| Concurrencia de escritura ajena | Lectura no bloquea. Una consulta puede ver el catálogo justo antes o después de un alta; nunca un agregado a medio escribir de *este* servicio (no escribe) |

## Error Handling

Excepciones de dominio en `services/` → HTTP en el router.

401 permanece simple (`{"detail": "Unauthorized"}`) para no filtrar existencia.

El resto de fallos de visibilidad de este GET usan **un solo** 404:

| Error Type | HTTP | Code | Response |
|------------|------|------|----------|
| Cabeceras ausentes/inválidas, cliente o tenant inactivo | 401 | — | `{"detail": "Unauthorized"}` |
| Vínculo inexistente, inactivo, otro tenant, o wholesaler mismatch | 404 | `PHOTOSHOOT_CATALOG_NOT_FOUND` | `{"detail": {"code": "PHOTOSHOOT_CATALOG_NOT_FOUND", "message": "Photoshoot catalog not found"}}` — idéntico en todos esos casos |
| `If-None-Match` desconocido | 200 | — | Catálogo completo (no es error) |
| `external_product_id` vacío / >255 | 422 | validación | FastAPI default |

No hay 403 en este endpoint. Las historias admiten `403`/`404`; se fija **404** para no crear un oráculo de existencia (ADR-040). El 403 de `create_link` (050) no se reutiliza aquí: en el alta el caller ya afirma el producto; en esta lectura un cliente ajeno no debe confirmarlo.

`resolve_active_link` puede lanzar errores más específicos. El servicio de catálogo los traduce todos a `PhotoshootCatalogNotVisibleError` **antes** de cualquier listado.

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| BFashion (intent 020) | Consume el GET para el formulario del staff | REST S2S; no se implementa el cliente |
| `get_service_client` | Auth fail-closed | Dependencia existente |
| `ProductLinkService.resolve_active_link` | Visibilidad del producto | Interno; sin cambio de contrato |
| `ImageTemplateRepository.list_selectable` | Plantillas common + private del dueño | Interno; este servicio filtra `active` |
| `ModelRepo` / `ModelPhotoRepo` | Modelos y poses del dueño | Interno |
| Presign MinIO existente | `preview_url` | Interno; solo en `200` |
| Constantes `cloth_type` / `VALID_POSES` | Fuente única del conjunto cerrado | Import; no tercer enum |

## Suggestion derivation

De las plantillas **ya incluidas** en `templates[]`:

- `background_suggestions`: valores `background` no nulos / no vacíos, distintos, ordenados.
- `color_suggestions`:
  - `null` → nada
  - `str` no vacío → ese valor
  - `list` → cada elemento string no vacío
  - otro tipo → se ignora (no tumba la agregación)

No se leen plantillas `draft`/`archived` ni privadas ajenas para sugerir.

## Logging

`core/logger.py`:

- info: `photoshoot_catalog_served` con `tenant_id`, `external_product_id`, `mayorista_id`, `catalog_version`, `template_count`, `model_count`, `not_modified`
- warn: `photoshoot_catalog_not_visible` con `system`, `tenant_id`, `external_product_id` — sin decir si el vínculo existe
- never: `X-Service-Secret`, `preview_url`, `minio_key`, `prompt`

## Testing plan (contrato; ejecución en Stage 5)

- 200: arrays presentes; `cloth_types` exactos; `max_pose_count == 3`
- `draft`/`archived` ausentes; `common` presente; `private` ajena ausente
- Modelo con 0 / 1 / 3 poses; `available_poses` reales y ordenadas
- Mayorista sin propias: `200`, `models[]` vacío, solo `common`
- Plantilla `colors=null` no rompe ni ensucia sugerencias
- 401 sin cabeceras / secreto inválido — sin queries de catálogo
- Otro tenant / inactivo / mismatch de wholesaler → 404 idéntico, sin cuerpo de catálogo
- Dos consultas sin cambios + `If-None-Match` → 304 sin cuerpo; `ETag` estable
- Archivar o revisar una plantilla activa, o alta de modelo / pose → `catalog_version` distinta; el ETag viejo ya no da 304
- `If-None-Match` basura → 200
- Respuesta y logs sin claves ni secretos
- `preview_url` ausente si no hay poses; presente y no igual a `minio_key` si hay foto

## Out of scope (reafirmado)

- Alembic, tablas, columnas, Redis, CDN, webhooks de invalidación, paginación
- Escritura de plantillas/modelos/poses
- `staff_id` / `resolve_staff_identity`
- Enum cerrado de `background`/`colors`
- Ensanchar el dueño a un mayorista-empresa (ADR-060)
- Editar `integration_service.py` o los GET del contrato B

## ADR candidates (Stage 3)

Decisiones que pueden merecer ADR:

1. **`CatalogVersion` = hash del conjunto visible**, no `max(updated_at)` ni tabla de contador — correctness al retirar filas vs. query más barata
2. **404 único en este GET** para todo fallo de resolve — aplica ADR-040; se desvía del 403 de `create_link` en 050
3. **ETag débil y presign diferido** — el cuerpo `200` no es byte-estable por `preview_url`

La ausencia de `staff_id` y la falta de Alembic son consecuencia directa del modelo; no requieren ADR salvo que se quiera registrar el 404 vs 403.

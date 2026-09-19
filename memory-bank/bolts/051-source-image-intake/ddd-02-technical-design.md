---
unit: 002-source-image-intake
bolt: 051-source-image-intake
stage: design
status: complete
updated: 2026-09-19T01:42:00Z
---

# Technical Design - source-image-intake

## Architecture Pattern

**Layered DDD dentro del monolito FastAPI**, el patrón del proyecto (`api/routers → services → repositories → models`).

No se introduce un bounded context hexagonal ni un router paralelo. El contrato C ya vive en `integration`; este bolt **añade** dos comandos y un agregado nuevo, reutilizando autenticación, vigencia de staff, resolución de vínculo y almacenamiento existentes.

Razones:

- `get_service_client` es el borde de autenticación de B y C.
- `StaffIdentityService.resolve_staff_identity` es el único gate de staff de C (ADR-057). Este bolt lo llama; no reimplementa vigencia.
- `ProductLinkService.resolve_active_link` ya es la autoridad de propiedad. El presign no infiere dueño.
- `StorageService.generate_upload_url` / `object_exists` / metadata del objeto es el precedente de `GET /api/prendas/upload-url`. No hay un segundo mecanismo de storage.
- El registro definitivo se **delega** en `tryoff_source_image_service` o `media_service` según `kind`. No hay cuarto almacén.

## Layer Structure

```text
┌─────────────────────────────────────────────────────────────┐
│ Presentation                                                │
│   api/routers/integration.py     +2 endpoints contrato C    │
│   api/schemas/integration.py     DTOs presign / confirm     │
├─────────────────────────────────────────────────────────────┤
│ Application                                                 │
│   services/source_image_intake_service.py   NUEVO           │
│   services/staff_identity_service.py        resolve (050)   │
│   services/product_link_service.py          resolve (047/050)│
├─────────────────────────────────────────────────────────────┤
│ Domain                                                      │
│   models/bridge_source_image.py             NUEVO           │
│   excepciones de dominio en services/                       │
├─────────────────────────────────────────────────────────────┤
│ Infrastructure                                              │
│   repositories/bridge_source_image_repo.py  NUEVO           │
│   StorageService                            reutilizado     │
│   tryoff_source_image_service / media_service  delegación   │
│   alembic/versions/*_bridge_source_images.py NUEVO          │
└─────────────────────────────────────────────────────────────┘
```

Responsabilidades por capa:

- **Router**: `Depends(get_service_client)`, traduce excepciones → HTTP, no contiene reglas.
- **Service**: validación previa a la firma, máquina de estados, observación del objeto, delegación de media, transacción.
- **Repository**: insert, lookup acotado a (`id`, `product_link_id`, `tenant_id`), transiciones atómicas `pending → ready|rejected`.
- **Model**: mapeo ORM + índices. `system`/`tenant_id` no se aceptan del cuerpo.

## Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Model | `models/bridge_source_image.py` | ORM `BridgeSourceImage`, máquina de estado, FKs |
| Repository | `repositories/bridge_source_image_repo.py` | `add`, `get_owned`, `transition_pending_to_ready`, `transition_pending_to_rejected` |
| Service | `services/source_image_intake_service.py` | `presign`, `confirm`; `reject` interno |
| Schema | `api/schemas/integration.py` | Request/response de los 2 endpoints; `extra = "ignore"` |
| Router | `api/routers/integration.py` | Registrar `:presign` y `:confirm` bajo `/api/integration/v1` |
| Auth | `core/dependencies.py` `get_service_client` | Reutilizado, sin cambios |
| Staff | `StaffIdentityService.resolve_staff_identity` | Reutilizado; no se llama `_authorize_staff` |
| Link | `ProductLinkService.resolve_active_link` | Reutilizado; no se toca `create_link` |
| Storage | `StorageService` | `generate_upload_url`, `object_exists`, `head_object` / metadata, presign GET de preview |
| Media | `tryoff_source_image_service` / `media_service` | Registro delegado; misma `AsyncSession`; **sin commit interno** |
| Const | `integration_service.STAFF_ROLES` | Solo vía `resolve_staff_identity`. **No se edita** `integration_service.py` |
| Config | `core/config.py` | `BRIDGE_SOURCE_IMAGE_UPLOAD_TTL_SECONDS=900`, `BRIDGE_SOURCE_IMAGE_MAX_BYTES` (defecto 10 MiB, mismo techo que `_validate_file`) |

## API Design

Base: `/api/integration/v1`. Auth: `X-Service-Id` + `X-Service-Secret`. Sin cookie.

Los schemas **no declaran** `system` ni `tenant_id`. Si el cliente los envía, `extra = "ignore"` los descarta.

### POST `/api/integration/v1/products/{external_product_id}/source-images:presign`

Reserva `pending` y emite el `UploadGrant`.

**Request**

```json
{
  "staff_id": "uuid",
  "kind": "garment_on_model | flat_garment",
  "content_type": "image/jpeg | image/png",
  "size_bytes": 1,
  "filename": "string",
  "external_wholesaler_id": "string | null"
}
```

**Response 201**

```json
{
  "source_image_id": "uuid",
  "upload_url": "https://…",
  "method": "PUT",
  "headers": { "Content-Type": "image/jpeg" },
  "expires_in": 900,
  "storage_key": "bridge/source-images/{product_link_id}/{source_image_id}"
}
```

`headers` es el conjunto que el navegador **debe** enviar para que la firma S3 coincida. No hay access key, secret, session token ni credencial de IA.

Dos presigns del mismo producto = dos reservas. El photoshoot elige por `source_image_id`.

### POST `/api/integration/v1/products/{external_product_id}/source-images/{source_image_id}:confirm`

Observa el objeto real y transiciona.

**Request**

```json
{
  "staff_id": "uuid",
  "checksum_sha256": "hex | null",
  "external_wholesaler_id": "string | null"
}
```

**Response 200** (primera vez o replay de `ready`)

```json
{
  "source_image_id": "uuid",
  "kind": "garment_on_model",
  "status": "ready",
  "content_type": "image/jpeg",
  "size_bytes": 123456,
  "preview_url": "https://…"
}
```

`content_type` / `size_bytes` son los **medidos**. `preview_url` es un GET presignado de vida corta (mismo TTL o uno menor, p. ej. 300 s); nunca la clave cruda.

## Data Persistence

### Tabla nueva `bridge_source_images`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `product_link_id` | UUID | NOT NULL, FK → `product_links.id` ON DELETE RESTRICT |
| `staff_id` | UUID | NOT NULL, FK → `mayoristas.id` ON DELETE RESTRICT |
| `tenant_id` | UUID | NOT NULL, FK → `tenants.id` |
| `kind` | VARCHAR | NOT NULL, check ∈ {`garment_on_model`, `flat_garment`} |
| `storage_key` | VARCHAR | NOT NULL, UNIQUE |
| `declared_content_type` | VARCHAR | NOT NULL, check ∈ {`image/jpeg`, `image/png`} |
| `declared_size_bytes` | INTEGER | NOT NULL, `> 0` |
| `actual_content_type` | VARCHAR | NULL hasta confirm |
| `actual_size_bytes` | INTEGER | NULL hasta confirm |
| `status` | VARCHAR | NOT NULL, default `pending`, check ∈ {`pending`, `ready`, `rejected`} |
| `rejection_reason` | VARCHAR | NULL; obligatorio si `rejected` |
| `registered_media_id` | UUID | NULL; obligatorio si `ready` |
| `registered_media_kind` | VARCHAR | NULL; `source_image` \| `garment_photo` si `ready` |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |
| `confirmed_at` | TIMESTAMPTZ | NULL; se rellena al pasar a `ready` o `rejected` |

Índices:

- `uq_bridge_source_images_storage_key` UNIQUE (`storage_key`)
- `ix_bridge_source_images_owned` (`tenant_id`, `product_link_id`, `id`) — lookup fail-closed
- `ix_bridge_source_images_link_status` (`product_link_id`, `status`)
- `ix_bridge_source_images_staff` (`staff_id`)

CHECK de coherencia (si el motor lo admite de forma portable; si no, el servicio es la autoridad):

- `status = 'ready'` ⇒ `registered_media_id` y `actual_*` NOT NULL
- `status = 'rejected'` ⇒ `rejection_reason` NOT NULL
- `status = 'pending'` ⇒ `registered_media_id` NULL

No hay unicidad «un origen por producto»: V1 admite N reservas.

### Tablas existentes

Sin migración de columnas en `product_links`, `mayoristas`, `tryoff_source_images` ni `garment_photos`. El registro delegado inserta en las tablas que esos servicios ya poseen.

### Clave de almacenamiento

```text
bridge/source-images/{product_link_id}/{source_image_id}
```

Bucket `originals` (el de media de origen del proyecto). El `filename` se sanea para logs/debug y **no** entra en la clave. Separadores de ruta y `..` se eliminan.

### Migración Alembic

Una revisión de esquema. Convención secuencial del repo. Downgrade: `DROP TABLE bridge_source_images`. Sin backfill.

## Use-case flows

### `presign`

1. Autenticar `ServiceClient`. Fail-closed → 401.
2. Validar body (Pydantic): `kind`, `content_type`, `size_bytes` (1..máximo), `filename` no vacío. Inválido → 422, **sin fila y sin firma**.
3. `staff = resolve_staff_identity(client, staff_id)`. Fallo → 403 `STAFF_FORBIDDEN`.
4. `link = resolve_active_link(client, external_product_id, external_wholesaler_id?)`.
   Ausente, inactivo, otro tenant, otro mayorista, wholesaler mismatch → 404 `PRODUCT_LINK_NOT_FOUND` (misma respuesta; sin oráculo).
5. Generar `source_image_id`. Construir `storage_key`.
6. `add` reserva `pending` (flush, no commit todavía).
7. `UploadGrant = StorageService.generate_upload_url(key, content_type, ttl)`.
   La firma S3 debe atar `PUT` + esa clave + `Content-Type` declarado. Otras claves/métodos las rechaza el almacenamiento.
8. Si el firmante falla: rollback de la reserva. Nunca 201 sin grant.
9. Commit. 201. No loguear `upload_url`.

### `confirm`

1. Autenticar cliente → 401 idéntico si falla.
2. `resolve_staff_identity` → 403 si el staff está revocado o no es vigente (también aquí).
3. `resolve_active_link` → 404 `PRODUCT_LINK_NOT_FOUND` si el producto no es operable.
4. `row = repo.get_owned(id, product_link_id=link.id, tenant_id=client.tenant_id)`.
   Ausente **o** de otro vínculo → 403 `SOURCE_IMAGE_FORBIDDEN`, mismo cuerpo. No se revela si el id existe.
5. Si `rejected` → 409 `SOURCE_IMAGE_REJECTED` (terminal; no se reabre).
6. Si `ready` → 200 replay: misma `RegisteredMediaRef`, `preview_url` recién firmado (GET). No se vuelve a registrar media.
7. Si `pending`:
   1. `SELECT … FOR UPDATE` de la fila `pending` (o equivalente atómico).
   2. `object_exists(storage_key)` falso → 409 `SOURCE_IMAGE_NOT_UPLOADED`; status sigue `pending`.
   3. `head_object` → `actual_content_type`, `actual_size_bytes`.
   4. Evaluar, en este orden:
      - tamaño real `0` o `> MAX` → reject `OBJECT_EMPTY` / `OBJECT_TOO_LARGE`
      - tipo real ∉ {`image/jpeg`, `image/png`} o ≠ declarado → reject `CONTENT_TYPE_MISMATCH`
      - tamaño real ≠ `declared_size_bytes` → reject `SIZE_MISMATCH`
      - `checksum_sha256` informado y distinto del digest del objeto → reject `CHECKSUM_MISMATCH`
      - bytes no decodificables / validador de `media_service._validate_file` → reject `UNREADABLE_IMAGE`
   5. Si reject: `transition_pending_to_rejected` + `actual_*` + motivo. 409 `SOURCE_IMAGE_REJECTED` con mensaje mostrable.
   6. Si ok: `MediaRegistrationGateway.register(kind, object, owner=link.mayorista_id)` **en la misma sesión**.
      - `garment_on_model` → `tryoff_source_image_service` → `registered_media_kind=source_image`
      - `flat_garment` → `media_service` → `registered_media_kind=garment_photo`
   7. `transition_pending_to_ready` con `actual_*`, media ref, `confirmed_at=now()`.
   8. Si la transición actualiza 0 filas (otra request ganó): releer. `ready` → replay 200. `rejected` → 409. Nunca una segunda media.
8. Commit único al final del request.

Igualdad declarado/real es **estricta** (FR-4). No se «corrige» un PNG declarado como JPEG.

Objeto sustituido entre `PUT` y confirm: se valida lo que hay **ahora**.

## Security Design

| Concern | Approach |
|---------|----------|
| Autenticación de servicio | `get_service_client`; 401 idéntico, sin revelar recurso |
| Autorización de staff | `resolve_staff_identity` en **ambos** comandos (ADR-057). Cookie/JWT de mayorista no aplican |
| Tenant isolation | `tenant_id` solo del cliente. `get_owned` exige `tenant_id` + `product_link_id`. Listener ADR-012 sigue |
| Propiedad | Se lee del `ProductLink` persistido, nunca del `external_product_id` suelto ni de la clave |
| Opacidad de reserva | Id ajeno e id inexistente → **mismo** 403 `SOURCE_IMAGE_FORBIDDEN` (historia 003). Producto no resoluble → 404, sin distinguir tenant/inactivo |
| Upload grant | TTL corto; `PUT` + una clave + `Content-Type`. La URL es el único material de acceso |
| Preview | GET presignado de vida corta; no se persiste; no se loguea |
| Secretos | Respuesta y logs sin access keys, secretos de MinIO, `X-Service-Secret`, ni API keys de IA (NFR-6, ADR-047) |
| Fail-closed | Cualquier duda rechaza. Discrepancia → `rejected`, nunca `ready` |
| Input | Pydantic enums/rangos. `filename` saneado. Path ids como UUID/`external_product_id` string |
| CORS / endpoint público | **Despliegue**, no código. Verificar `MINIO_PUBLIC_ENDPOINT` y CORS del bucket `originals` antes de implementar. Sin multipart de respaldo |

### Resolución de la tensión ADR-040 vs historias

| Caso | HTTP | Por qué |
|------|------|---------|
| Sin credenciales de servicio | 401 | No autenticado; cuerpo idéntico |
| Staff inválido/revocado | 403 | FR-15 explícito |
| Producto no resoluble (ausente, inactivo, otro tenant, otro mayorista) | 404 | El path trae `external_product_id`; no se oracula *por qué* no opera. Espíritu ADR-040 |
| `source_image_id` ausente o de otro `product_link` | 403 | Historia 003 exige 403 **y** la misma respuesta que «no existe». Opacidad entre ambos |
| Objeto aún no subido | 409 | Conflicto reintentable; no es un secreto de existencia ajena |

No se usa 404 para la reserva: si el producto ya resolvió, 404 vs 403 en el id filtraría existencia. Un solo código (403) cumple opacidad y el texto de la historia.

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| NFR-1 p95 ≤ 1 s (sin transferencia del archivo) | Presign: 2 lookups indexados + insert + 1 firma S3. Confirm: lookups + `HeadObject` + validación local ≤ 10 MiB + un insert de media. Sin Celery. Decode local es el único riesgo; se acota al máximo configurado |
| NFR-6 aislamiento y secretos | Ver Security. Tests: 401/403/404/409 y ausencia de secretos / URLs en logs |
| Idempotencia de confirm | Autoridad = transición `WHERE status='pending'` (ADR-010 / ADR-054 / ADR-050). Replay de `ready` es lectura |
| Durabilidad | Un `commit` por request. Media y transición en la misma transacción |
| Escalabilidad | 1 fila por intento de subida. Sin caché. Purga de `pending` caducadas = fuera de alcance |
| Disponibilidad del PUT | El navegador habla con MinIO/S3. Si no alcanza el endpoint público, se corrige infra, no se añade camino |

## Error Handling

Excepciones de dominio en `services/` → HTTP en el router.

Forma: `{"detail": {"code": "...", "message": "...", "context": {}}}` para dominio; `{"detail": "Unauthorized"}` para 401.

`message` es mostrable al staff. `context` puede llevar `source_image_id` y `status` cuando el caller ya es dueño. Nunca `storage_key` cruda en errores de acceso ajeno, nunca URLs, nunca rutas de filesystem.

| Error Type | HTTP | Code | Response |
|------------|------|------|----------|
| Cabeceras ausentes/inválidas, cliente o tenant inactivo | 401 | — | `{"detail": "Unauthorized"}` idéntico |
| Staff desconocido, sin rol, otro tenant, o revocado | 403 | `STAFF_FORBIDDEN` | sin firmar / sin registrar |
| Vínculo ausente, inactivo, otro tenant, otro mayorista, wholesaler mismatch | 404 | `PRODUCT_LINK_NOT_FOUND` | genérico; sin firmar |
| `source_image_id` inexistente o de otro producto | 403 | `SOURCE_IMAGE_FORBIDDEN` | mismo cuerpo; sin revelar existencia |
| Objeto ausente al confirmar | 409 | `SOURCE_IMAGE_NOT_UPLOADED` | reserva sigue `pending` |
| Reserva ya `rejected`, o se acaba de rechazar | 409 | `SOURCE_IMAGE_REJECTED` | `rejection_reason` mostrable; sigue `rejected` |
| `kind` / `content_type` / `size_bytes` / `filename` inválidos en presign | 422 | validación Pydantic | sin fila, sin URL |
| Fallo del firmante S3 tras validar | 503 | `STORAGE_UNAVAILABLE` | rollback; sin 201 |

401 no usa código rico: no se filtra si el producto o la reserva existen.

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| BFashion (intent 020) | Pide presign, hace `PUT` desde el navegador del staff, llama confirm | REST S2S + PUT directo a MinIO/S3 |
| MinIO / S3 | Firma, `HeadObject`, existencia, preview GET | `StorageService`; bucket `originals` |
| `StaffIdentityService` | Vigencia de `staff_id` | Interno (bolt 050) |
| `ProductLinkService` | Resolución fail-closed del vínculo | Interno |
| `tryoff_source_image_service` | Registro `garment_on_model` | Interno; misma sesión |
| `media_service` / `MediaUploadService` | Registro `flat_garment` + `_validate_file` | Interno; misma sesión |
| PostgreSQL | Persistencia de reservas | SQLAlchemy async |
| Navegador del staff | Ejecuta el `PUT` | Fuera de este repo; CORS es despliegue |

## Transaction & concurrency

- `presign`: insert + firma; commit al final. Firma fallida → rollback.
- `confirm` de `pending`: `SELECT FOR UPDATE` → observar objeto → (reject update **o** register media + ready update) → un commit.
- Dos confirms concurrentes: uno gana el lock; el otro espera, relee `ready` y hace replay. El gateway de media **no** se llama dos veces.
- Si el servicio de media no acepta sesión compartida (hallazgo de implementación): no commitear media antes de la transición; abortar y adaptar el servicio **mínimo** para aceptar sesión, no crear un almacén paralelo.
- No Redis. No Celery. No lease de proveedor.

## Logging

`core/logger.py`, estructurado:

- info: `source_image_reserved`, `source_image_ready`, `source_image_confirm_replayed` con ids, `kind`, `status`, `tenant_id`, `product_link_id`
- warn: `source_image_rejected`, `source_image_not_uploaded`, `source_image_forbidden` con **código**, no con URL
- never: `upload_url`, `preview_url`, `X-Service-Secret`, access keys, checksums completos en info (debug a lo sumo)

## Testing plan (contrato; ejecución en Stage 5)

- Presign 201: campos requeridos, `method=PUT`, `headers`, `expires_in`, fila `pending` no utilizable
- `content_type` / `size_bytes` / `kind` inválidos → 422, sin fila, sin URL
- Vínculo irresoluble → 404, sin firma
- Staff revocado → 403 en presign **y** confirm
- 401 sin cabeceras, mismo cuerpo
- Respuesta y logs sin secretos ni URLs
- Confirm con objeto presente y coherente → 200 `ready`; `garment_on_model` registra `SourceImage`; `flat_garment` registra `GarmentPhoto`
- Reconfirm `ready` → 200 mismo id, una sola media
- Dos confirms concurrentes → una media
- Objeto ausente → 409, sigue `pending`, segundo confirm tras `PUT` puede pasar
- Tipo/tamaño discrepantes, 0 bytes, no decodificable, checksum malo → `rejected` + 409; nunca `ready`
- Reconfirm `rejected` → 409, sigue `rejected`
- Reserva de otro `product_link` → 403; id inexistente → **mismo** 403
- ServiceClient de otro tenant → 404 de producto, sin registrar
- `filename` con `../` no aparece en `storage_key`
- Firma acotada: el diseño asume que el storage rechaza otra clave/otro método (se documenta; el test de Stage 5 mockea o usa MinIO de test)

## Out of scope (reafirmado)

- Multipart de respaldo, transformaciones, miniaturas, purga de `pending`/`rejected`, cambiar cookie-upload, photoshoot, CORS como código, modificar `integration_service.py`.

## ADR candidates (Stage 3)

1. **403 único para reserva ausente o ajena** — matiz explícito de ADR-040 para no oracular existencia una vez resuelto el producto.
2. **Confirm atómico + media en la misma sesión** — una sola media bajo carrera; los servicios de media no commitean solos.
3. **Igualdad estricta declarado/real** — FR-4 al pie de la letra; no se «salva» un PNG etiquetado como JPEG.
4. **Clave determinista `bridge/source-images/{product_link_id}/{source_image_id}`** — propiedad legible en la clave; el filename no participa.

Los puntos 1 y 2 tienen más peso ADR (afectan bolts 053 y el patrón de delegación). 3 y 4 son consecuencia directa de las historias; se pueden saltar si no aportan.

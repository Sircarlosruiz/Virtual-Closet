---
unit: 002-source-image-intake
bolt: 051-source-image-intake
stage: model
status: complete
updated: 2026-09-19T01:35:00Z
---

# Static Model - source-image-intake

## Bounded Context

**Admisión de imagen de origen** (Source Image Intake).

Este contexto cierra G1: es el único camino por el que BFashion entrega bytes a Virtual Closet. Autoriza *quién* sube, *sobre qué producto* y *qué clase de origen*, reserva una clave, deja que el navegador del staff ponga los bytes **directo** en el almacenamiento, y después verifica el objeto real antes de declarar la reserva utilizable.

Virtual Closet es la única autoridad del ciclo de vida de la reserva. BFashion no posee el objeto ni el registro de media. Los bytes no atraviesan el backend de BFashion ni el de Virtual Closet. No hay camino multipart de respaldo: si el navegador no alcanza el endpoint público de MinIO/S3, se corrige el despliegue.

**Dentro del contexto**
- Reservar una subida (`pending`) y emitir un permiso de `PUT` acotado a una clave
- Verificar el objeto real (existencia, tipo, tamaño, decodificabilidad, checksum opcional)
- Transicionar a `ready` o `rejected`
- Delegar el registro definitivo en los almacenes de media existentes según `kind`
- Rechazar fail-closed: vínculo ajeno, tenant ajeno, staff revocado, discrepancia declarado/real

**Fuera del contexto**
- Crear o reactivar `ProductLink` / `StaffIdentityLink` (unidad 001, bolt 050)
- Disparar o orquestar photoshoots (unidad 003)
- Endpoints cookie-auth de subida (`/api/prendas/upload`, `/api/media/garments`, `/api/tryoff/source-images`)
- Transformaciones, miniaturas, biblioteca de media, cuarentena antivirus
- Purga de reservas `pending` caducadas o `rejected`
- Configuración CORS y `MINIO_PUBLIC_ENDPOINT` (despliegue)

Contextos vecinos: **Aprovisionamiento del puente** (`ProductLink`, `resolve_staff_identity`), **Tenancy / Auth** (`ServiceClient`), **Media de origen existente** (`SourceImage`, `GarmentPhoto`), **Almacenamiento de objetos** (MinIO/S3), **Photoshoot** (consume solo reservas `ready`).

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| **BridgeSourceImage** (nueva, raíz) | `id`, `product_link_id`, `staff_id`, `kind` (`garment_on_model` \| `flat_garment`), `storage_key`, `declared_content_type`, `declared_size_bytes`, `actual_content_type?`, `actual_size_bytes?`, `status` (`pending` \| `ready` \| `rejected`), `rejection_reason?`, `registered_media_id?`, `registered_media_kind?`, `tenant_id`, `created_at`, `confirmed_at?` | Una reserva = un intento de subida. Nace `pending` y no es utilizable para generar. Solo `ready` lo es. `rejected` es terminal para esa reserva: no se recicla. `kind`, `storage_key` y lo declarado son inmutables tras el alta. `tenant_id` sale del `ServiceClient`. `staff_id` es el espejo vigente en el momento del presign; la vigencia se vuelve a comprobar al confirmar. La propiedad se lee del `product_link_id`, no del tenant solo. El registro de media ocurre solo en la transición a `ready`, una vez, y se anota en `registered_media_id` / `registered_media_kind`. Dos presigns del mismo producto son dos reservas independientes. |
| **ProductLink** (existente, referenciada) | `id`, `system`, `external_product_id`, `mayorista_id`, `tenant_id`, `is_active`, `external_wholesaler_id?` | Ancla de propiedad. El presign y la confirmación exigen un vínculo **activo** resoluble por el `ServiceClient`. Un vínculo inactivo, de otro tenant o de otro mayorista no firma ni registra. `mayorista_id` es el espejo del staff que creó el vínculo (ADR-060); este contexto no inventa un dueño de empresa. |
| **ServiceClient** (existente, actor) | `id`, `system`, `tenant_id`, `is_active` | Identidad del backend llamante. Credenciales ausentes, inválidas, cliente inactivo o tenant inactivo → fail-closed; no se firma, no se revela existencia. Aporta `system` y `tenant_id`; nunca se leen del cuerpo. |
| **Mayorista** (existente, espejo referenciado) | `id`, `role`, `tenant_id` | El `staff_id` asertado se resuelve con `StaffIdentityService.resolve_staff_identity` (ADR-057): existe, mismo tenant, rol en `STAFF_ROLES`, y `StaffIdentityLink` **activo**. Un espejo revocado recibe 403 en presign **y** en confirm. No se usa `_authorize_staff`. |
| **StoredObject** (concepto, no fila ORM) | clave, existencia, `content_type` real, `size_bytes` real, bytes decodificables, digest SHA-256 | Autoridad de lo que hay en el bucket. Lo declarado en el presign no se cree. Ausente → la reserva sigue `pending` (reintentable). Presente pero incoherente, vacío, no decodificable o con checksum distinto → `rejected`. |
| **SourceImage** (existente, destino, fuera de este agregado) | identidad de media TryOff | Destino del registro cuando `kind = garment_on_model`. Este contexto **no** modela su ciclo interno; delega en `tryoff_source_image_service`. |
| **GarmentPhoto** (existente, destino, fuera de este agregado) | identidad de media VTON | Destino del registro cuando `kind = flat_garment`. Delegación en `media_service` / `MediaUploadService`. No se crea un cuarto almacén paralelo. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| **SourceImageId** | UUID | Identidad de la reserva. Se emite al presign. El photoshoot referencia este id, no la clave de almacenamiento. |
| **SourceImageKind** | `garment_on_model` \| `flat_garment` | Conjunto cerrado. Cualquier otro valor es inválido **antes** de firmar. Inmutable. Determina el almacén de media, no el pipeline (el photoshoot leerá `kind` / `input_kind`). |
| **SourceImageStatus** | `pending` \| `ready` \| `rejected` | Máquina: `pending → ready` o `pending → rejected`. `ready` y `rejected` son terminales. No existe `pending → ready → rejected`. |
| **DeclaredContentType** | `image/jpeg` \| `image/png` | Validado antes de firmar. Otro tipo → invariante de valor; no hay reserva ni URL. |
| **DeclaredSizeBytes** | entero | `1..límite` (precedente: 10 MB de `media_service._validate_file`). `0` o exceso → no se firma. |
| **ActualContentType** | tipo medido del objeto | Se rellena al confirmar. Si contradice lo declarado → rechazo terminal. |
| **ActualSizeBytes** | entero medido | Se rellena al confirmar. Si supera el límite o contradice lo declarado de forma material → rechazo. Objeto de 0 bytes → rechazo. |
| **StorageKey** | texto | Patrón determinista que incluye `product_link_id` y `source_image_id`. El `filename` **nunca** llega crudo a la clave (se sanea; se ignoran separadores de ruta y no-ASCII peligrosos). La propiedad es legible desde la clave, pero la autoridad de acceso sigue siendo el agregado + el vínculo. |
| **UploadGrant** | `upload_url`, `method = PUT`, `headers`, `expires_in`, `storage_key` | Permiso de vida corta (TTL configurable; propuesta 900 s, alineado al contrato A). Solo autoriza `PUT` sobre la clave emitida. No es un secreto de cuenta: es una URL acotada. La respuesta jamás añade credenciales de almacenamiento ni de proveedor de IA. Caducado: el `PUT` falla en el almacenamiento; la reserva sigue `pending`. |
| **PreviewUrl** | URL presignada de **descarga** de vida corta | Solo en `ready`. Regenerable. Nunca se expone la clave como si fuese pública. |
| **RejectionReason** | código + mensaje | Concreto para que BFashion lo muestre al staff. Sin rutas internas, claves, credenciales ni existencia de reservas ajenas. |
| **ObjectChecksum** | SHA-256 opcional | Si el cliente lo envía al confirmar y no coincide con el objeto real → `rejected`. Si no se envía, no se exige. |
| **SanitizedFilename** | texto | Entrada humana. Se sanea; no forma la identidad ni la propiedad. |
| **StaffId** | UUID | Espejo asertado. Debe pasar `resolve_staff_identity` en **ambas** operaciones. |
| **TenantId** | UUID | Solo del `ServiceClient`. |
| **SystemName** | texto | Solo del `ServiceClient`. |
| **RegisteredMediaRef** | `registered_media_id` + `registered_media_kind` | Puntero al almacén delegado. Nulo mientras `pending` o `rejected`. Inmutable tras `ready`. Permite a la orquestación saber qué servicio consumir. |
| **ExternalProductId** | texto | Identifica el producto borrador. No implica propiedad: se resuelve a `ProductLink`. |
| **ExternalWholesalerId** | texto opcional | Si se envía, se compara fail-closed con el persistido en el vínculo (misma regla que `resolve_active_link`). No selecciona otro dueño (ADR-060). |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| **BridgeSourceImage** | Declaración (`kind`, tipo/tamaño declarados, `storage_key`); observación (`actual_*`); estado; `RejectionReason?`; `RegisteredMediaRef?`; referencias a `ProductLink`, `StaffId`, `TenantId` | (1) Nace `pending` con declaración válida; sin declaración válida no hay agregado. (2) Solo `ready` es utilizable para generar; `pending` y `rejected` no lo son. (3) `rejected` es terminal: confirmar de nuevo no reabre. (4) `ready` es idempotente: reconfirmar devuelve la misma reserva y **no** registra una segunda media. (5) La transición a `ready` exige objeto existente, tipo admitido, tamaño dentro de límite, imagen decodificable, coherencia declarado/real, y checksum válido si se envió. (6) Objeto ausente: no se transiciona; sigue `pending` (reintento de `PUT` + confirm). (7) Discrepancia, vacío, no decodificable o checksum inválido → `rejected`, nunca `ready`. (8) `kind`, clave y declaración son inmutables. (9) `tenant_id` y `system` del cliente; nunca del cuerpo. (10) La propiedad es el `product_link_id` resuelto; mismo tenant y otro producto = acceso denegado. (11) El staff debe estar vigente al presign **y** al confirmar; revocar entre ambos bloquea el confirm. (12) El registro de media ocurre como máximo una vez, en la transición a `ready`, según `kind`. (13) Confirmaciones concurrentes: una registra, la otra observa el mismo `ready`; nunca dos medias. (14) Cross-tenant / reserva ajena: rechazo sin revelar si la reserva o el objeto existen. (15) La respuesta no contiene secretos de almacenamiento ni de IA. |

`ProductLink`, `ServiceClient` y `Mayorista` siguen siendo raíces de sus contextos. Este bolt las **usa**; no las rediseña. `SourceImage` y `GarmentPhoto` no se convierten en miembros del agregado: se referencian tras la delegación.

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| **SourceImageReserved** | Alta de la reserva `pending` + emisión del `UploadGrant` | `source_image_id`, `product_link_id`, `staff_id`, `kind`, `storage_key`, `expires_in` |
| **SourceImagePresignDenied** | Invariante violado antes de firmar (tipo, tamaño, `kind`, vínculo, staff, tenant) | `external_product_id`, `reason` — sin URL |
| **SourceImageBecameReady** | Primera confirmación que verifica el objeto y registra media | `source_image_id`, `kind`, `registered_media_id`, `registered_media_kind`, `actual_content_type`, `actual_size_bytes` |
| **SourceImageConfirmationReplayed** | Confirm de una reserva ya `ready` | `source_image_id`, misma `RegisteredMediaRef` |
| **SourceImageConfirmationDeferred** | Confirm con objeto ausente | `source_image_id`, `status` sigue `pending`, motivo de conflicto reintentable |
| **SourceImageRejected** | Confirm que observa incoherencia, vacío, no decodificable, checksum inválido o tamaño ilegal | `source_image_id`, `rejection_reason`, `actual_content_type?`, `actual_size_bytes?` |
| **SourceImageAccessDenied** | Reserva o producto ajenos, staff revocado, cliente de otro tenant | `external_product_id`, `source_image_id?`, `reason` — **sin filtrar existencia** |

Estos eventos documentan el lenguaje del dominio. V1 no exige un bus: bastan persistencia + logs estructurados **sin** URLs presignadas ni secretos (coding standards: nunca loguear URLs de MinIO).

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| **SourceImageIntakeService** (nuevo) | `presign(client, external_product_id, staff_id, kind, content_type, size_bytes, filename, external_wholesaler_id?) → (BridgeSourceImage, UploadGrant)`; `confirm(client, external_product_id, source_image_id, staff_id, checksum?, external_wholesaler_id?) → BridgeSourceImage`; `reject(reservation, reason)` interno | `StaffIdentityService.resolve_staff_identity`, resolución activa de `ProductLink`, `BridgeSourceImageRepository`, puerto de almacenamiento, puertos de registro de media |
| **MediaRegistrationGateway** (puerto, no almacén nuevo) | `register(kind, object, owner) → RegisteredMediaRef` | `tryoff_source_image_service` si `garment_on_model`; `media_service` / `MediaUploadService` si `flat_garment` |
| **StorageGranting** (existente, se reutiliza) | `grant_put(key, content_type, ttl) → UploadGrant`; `object_exists(key)`; `head_object(key) → ObjectReality`; `grant_get(key, ttl) → PreviewUrl` | `StorageService.generate_upload_url` / `object_exists` / metadata del objeto. No se introduce un mecanismo de almacenamiento nuevo. |
| **StaffIdentityService** (existente, bolt 050) | `resolve_staff_identity(client, staff_id) → Mayorista` | Único punto de vigencia del staff en contrato C (ADR-057) |
| **ServiceAuthentication** (existente, no se modifica) | Verifica `X-Service-Id` / `X-Service-Secret` fail-closed | `ServiceClientRepository` |

Reglas de servicio:

- `presign` valida `kind`, tipo y tamaño **antes** de persistir y **antes** de firmar. Un rechazo de valor no deja fila.
- `presign` exige vínculo activo + staff vigente. Sin ambos, no hay reserva ni URL.
- `confirm` vuelve a exigir vínculo activo + staff vigente + que la reserva pertenezca a **ese** vínculo.
- `confirm` observa el objeto real; no confía en la declaración. La declaración sirve para detectar discrepancia, no para rellenar `ready`.
- Objeto ausente es conflicto **reintentable** (`pending` se conserva). Rechazo de contenido es terminal.
- Idempotencia de `confirm` es de **estado**, no de clave HTTP: `ready` se relee; no hay `Idempotency-Key` en esta unidad.
- Confirmaciones concurrentes: la autoridad es una transición atómica `pending → ready` (o `pending → rejected`). Quien pierde la carrera relee. Patrón de colisión ADR-010 / ADR-054 / ADR-050.
- Fail-closed: credenciales inválidas no distinguen si el producto o la reserva existen. Reserva de otro producto: misma opacidad hacia fuera.
- Nunca reimplementar vigencia de staff; siempre `resolve_staff_identity`.
- Nunca crear un cuarto almacén de origen.

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| **BridgeSourceImageRepository** (nuevo) | `BridgeSourceImage` | `add(reservation)`; `get_by_id(id)`; `get_owned(id, product_link_id, tenant_id)`; `save(reservation)`; `transition_pending_to_ready(id, actual, media_ref)` / `transition_pending_to_rejected(id, reason, actual?)` atómicos |
| **ProductLinkRepository** (existente, solo lectura) | `ProductLink` | `resolve_active_link` / `resolve_owned_link` — no cambia de contrato |
| **StaffIdentity resolution** (existente) | `Mayorista` + `StaffIdentityLink` | `resolve_staff_identity` — no se reimplementa aquí |
| **ServiceClientRepository** (existente, solo lectura) | `ServiceClient` | Resolución que ya usa la autenticación de servicio |
| **ObjectStorage** (existente) | `StoredObject` | `generate_upload_url`; `object_exists`; `head_object`; presign de descarga para `preview_url` |
| **MediaRegistrationGateway** | `SourceImage` \| `GarmentPhoto` | Registro delegado; este repositorio no inserta esas tablas a mano |

La transición de estado vive en el repositorio/esquema (update condicional `WHERE status = 'pending'`), no solo en el servicio. El servicio traduce «0 filas actualizadas» a replay (`ready`/`rejected` ya terminal) o a carrera ganada por otro.

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Imagen de origen / Source image** | Reserva `BridgeSourceImage` que representa un intento de entregar bytes para un producto del puente. No es todavía media utilizable. |
| **Reserva** | La fila `pending`. Ocupa un `source_image_id` y una clave. No genera. |
| **Presign** | Operación que valida, reserva y emite un `UploadGrant`. |
| **UploadGrant** | Permiso `PUT` de vida corta acotado a una clave. No es una credencial de cuenta. |
| **Subida directa** | El navegador del staff hace `PUT` al almacenamiento. Ningún backend ve los bytes. |
| **Confirmación** | Operación que observa el objeto real y transiciona a `ready` o `rejected`. |
| **Ready** | Reserva verificada, media registrada, usable como entrada de photoshoot. |
| **Rejected** | Reserva terminal inválida. Recuperación = nuevo presign, no reciclar. |
| **Pending** | Esperando bytes verificables. Ausencia de objeto no la mata. |
| **kind** | Clase de origen: prenda sobre modelo (`garment_on_model`) o prenda plana (`flat_garment`). |
| **Declarado** | Tipo y tamaño afirmados al presign. Hipótesis, no verdad. |
| **Real / medido** | Tipo, tamaño y decodificabilidad del objeto en el momento de confirmar. |
| **Discrepancia declarado/real** | El objeto no es lo que se afirmó. Siempre `rejected`. |
| **Utilizable** | Solo `ready`. El photoshoot rechaza cualquier otro estado. |
| **Fail-closed** | Ante duda (credencial, tenant, staff, vínculo, propiedad, contenido) se rechaza y no se registra media. |
| **Sin filtrar existencia** | Reserva ajena e inexistente se responden igual hacia un llamante que no es dueño. |
| **Delegación de media** | Registrar en `SourceImage` o `GarmentPhoto` según `kind`, sin un cuarto almacén. |
| **Cuarto almacén** | Un sitio nuevo de bytes de origen. Prohibido. Ya hay prenda, `garment_photos` y `tryoff_source_images`. |
| **Contrato C** | Superficie nueva del intent 009. Este bolt entrega `source-images:presign` y `:confirm`. |
| **G1** | Hueco: BFashion no tenía forma de entregar bytes. Este contexto lo cierra. |

## Decisiones de dominio que condicionan el diseño

1. **Un agregado, dos operaciones.** Presign crea la reserva; confirm observa la realidad. No hay un agregado distinto para el permiso: el `UploadGrant` es un valor emitido, no una entidad.
2. **La verdad está en el objeto.** Lo declarado solo sirve para firmar con una hipótesis y para detectar mentira. `ready` se escribe con lo medido, y solo si coincide con lo declarado y con las reglas de media.
3. **Ausencia ≠ rechazo.** Sin objeto se queda `pending` (el staff puede terminar el `PUT`). Contenido malo es terminal. Mezclarlos haría irrecuperable un `PUT` tardío.
4. **Rechazo terminal por reserva, no por producto.** El camino de recuperación es un presign nuevo. Así no hay estados ambiguos ni reescritura de una reserva condenada.
5. **Dos reservas por producto son legales.** El photoshoot elige por `source_image_id`. No hay unicidad «un origen por producto» en V1.
6. **Propiedad = ProductLink, no tenant.** Un id de reserva de otro producto del mismo tenant es tan ajeno como uno de otro tenant. ADR-060: el dueño del vínculo es el espejo; no se busca un mayorista de empresa.
7. **Vigencia de staff en las dos puertas.** ADR-057: `resolve_staff_identity` en presign y confirm. Revocar entre ambos impide registrar.
8. **Delegación, no duplicación.** `kind` elige el servicio de media existente. Este contexto guarda el puntero, no los bytes lógicos de TryOff/VTON.
9. **Idempotencia de confirm es de estado.** A diferencia del photoshoot (clave HTTP), aquí reconfirmar `ready` es un replay. La carrera se resuelve con transición atómica.
10. **Sin segundo camino.** Producto: solo presign + confirm. CORS / endpoint público son despliegue. El modelo no contempla multipart.
11. **Sin secreto en la respuesta.** Ni claves de cuenta, ni secretos de IA, ni `preview_url` que sea la clave cruda. El `UploadGrant` es el único material de acceso y está acotado.
12. **Taxonomía de rechazo** (HTTP exacto en Stage 2; aquí el significado):
    - Cliente de servicio ausente/inválido → no autenticado
    - `staff_id` inválido o revocado → no autorizado (ambas operaciones)
    - Vínculo inexistente, inactivo o de otro tenant/mayorista → no encontrado / no autorizado; **sin firmar**
    - Reserva de otro `product_link` → acceso denegado **sin filtrar existencia** (espíritu ADR-040; las historias escriben 403)
    - `kind` / tipo / tamaño declarados inválidos → invariante de valor, antes de persistir
    - Objeto ausente al confirmar → conflicto reintentable; sigue `pending`
    - Discrepancia, 0 bytes, no decodificable, checksum, tamaño real ilegal → rechazo terminal
    - Reconfirm de `rejected` → conflicto; sigue `rejected`
    - Reconfirm de `ready` → replay exitoso
13. **Tensión ADR-040 vs historias (para Stage 2).** ADR-040 pide 404 en recursos no poseídos para no filtrar existencia. Las historias 001/003 mezclan 403/404 y piden 403 explícito en reserva ajena, con la misma opacidad «ajena ≡ inexistente». El dominio exige opacidad; el código HTTP se fija en diseño técnico.

## Story Coverage

| Story | Cubierta por |
|-------|----------------|
| **001-source-image-presign** | `SourceImageIntakeService.presign`; VOs `SourceImageKind`, `DeclaredContentType`, `DeclaredSizeBytes`, `UploadGrant`, `StorageKey`, `SanitizedFilename`; evento `SourceImageReserved` / `SourceImagePresignDenied`; invariantes de validación previa a la firma, TTL, `PUT`-only, no-secreto, no-utilizable en `pending` |
| **002-source-image-confirm** | `confirm`; observación de `StoredObject`; transición a `ready`; `MediaRegistrationGateway` por `kind`; `PreviewUrl`; idempotencia de estado; evento `SourceImageBecameReady` / `Replayed` / `Deferred`; invariante de una sola media; checksum opcional |
| **003-source-image-rejection** | Invariantes fail-closed de propiedad, tenant y staff; discrepancia declarado/real; no decodificable; tamaño real; `rejected` terminal; evento `SourceImageRejected` / `SourceImageAccessDenied`; `RejectionReason` mostrable; opacidad de existencia |

## Prior Decisions Applied

- **ADR-057**: presign y confirm llaman a `resolve_staff_identity`; no a `_authorize_staff`.
- **ADR-060**: el dueño visible del producto sigue siendo `product_link.mayorista_id` (espejo). Este bolt no introduce un mayorista de empresa.
- **ADR-058**: el espejo se reconoce por `StaffIdentityLink`, no por una columna en `Mayorista`. Solo importa vía `resolve_staff_identity`.
- **ADR-012**: `tenant_id` siempre del `ServiceClient`; ninguna consulta nueva relaja el alcance.
- **ADR-040**: no filtrar existencia cross-tenant / cross-product. Código HTTP exacto se decide en Stage 2.
- **ADR-010 / ADR-054**: la autoridad de «una sola transición / una sola media» vive en persistencia (update condicional), no solo en el servicio.
- **ADR-047 / NFR-6 / coding standards**: ningún secreto de proveedor ni URL presignada en logs; la respuesta solo lleva el `UploadGrant` acotado.
- **ADR-051** no aplica: no hay visibilidad staff-vs-admin de plantillas; el aislamiento es tenant + `ProductLink`.
- **ADR-001**: este contexto es servidor-a-servidor (contrato C). No abre sesión cookie del espejo.

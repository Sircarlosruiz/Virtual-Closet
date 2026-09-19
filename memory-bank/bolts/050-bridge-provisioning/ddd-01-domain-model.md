---
unit: 001-bridge-provisioning
bolt: 050-bridge-provisioning
stage: model
status: complete
updated: 2026-09-19T00:36:16Z
---

# Static Model - bridge-provisioning

## Bounded Context

**Aprovisionamiento del puente** (Bridge Provisioning).

Este contexto es la capa de **identidad y propiedad** del puente BFashion ↔ Virtual Closet. Autoriza *quién* puede operar y *sobre qué producto*, antes de que existan imágenes, photoshoots o publicaciones.

Virtual Closet es la única autoridad de estos mapeos. BFashion posee el producto borrador y la sesión del staff; aquí solo se persiste el vínculo explícito y el espejo del actor. Ningún identificador externo (SKU, slug, PK de Django) infiere propiedad por sí solo.

**Dentro del contexto**
- Crear y resolver el vínculo explícito de producto (`ProductLink`)
- Aprovisionar, reactivar y revocar la identidad de staff espejo (`StaffIdentityLink` + `Mayorista` espejo)
- Validar que un `staff_id` asertado sigue vigente (punto único de autorización)

**Fuera del contexto**
- Autenticación por cookie del espejo (el espejo no es una cuenta usable)
- Tabla `StaffIntegrationIdentity` y `manage.py link_staff_identity` (intent 020, BFashion)
- Presign, photoshoot, catálogo, publicación
- Reactivar, editar o listar `ProductLink` por el puente
- Cancelar trabajo en vuelo al revocar
- Cambiar `_authorize_staff` / `STAFF_ROLES`: el espejo se crea para satisfacer la regla existente

Contextos vecinos: **Tenancy / Auth** (`ServiceClient`, `Tenant`, `Mayorista` real), **Integración ya entregada** (resolución de vínculo, autorización de staff), **Photoshoot** (consume vínculos e identidades vigentes).

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| **ProductLink** (existente, raíz) | `id`, `system`, `external_product_id`, `external_wholesaler_id?`, `mayorista_id`, `prenda_id?`, `tenant_id`, `is_active`, `created_by`, `created_at` | Unicidad `(system, external_product_id)`. `system` y `tenant_id` salen del `ServiceClient`, nunca del cuerpo. `mayorista_id` se resuelve desde la identidad de staff vigente y el tenant del cliente; nunca de un SKU ni de un id externo. `created_by` es el `staff_id` autorizado. Crear no reactiva un vínculo `is_active = false` (conflicto). Un `prenda_id` ajeno al mayorista del vínculo impide el alta. Cross-tenant sobre el mismo par único no muta filas. |
| **StaffIdentityLink** (nueva, raíz) | `id`, `system`, `external_staff_id`, `mayorista_id`, `tenant_id`, `is_active`, `created_at`, `revoked_at?` | Unicidad `(system, external_staff_id)`, simétrica a `ProductLink`. Un vínculo, un espejo: reaprovisionar devuelve el mismo `mayorista_id`. Revocar es lógica (`is_active = false`, `revoked_at` informado); nunca borra el `Mayorista` ni las FKs históricas. Reaprovisionar un vínculo revocado lo reactiva con el mismo UUID. El mismo `external_staff_id` en dos `system` son dos vínculos distintos. |
| **Mayorista** (existente, referenciada) | `id`, `email`, `role`, `tenant_id`, `password_hash` | El espejo es una fila `Mayorista` con `role ∈ {admin, owner, staff}` y `tenant_id` del `ServiceClient`. No es una cuenta usable: el hash de contraseña es aleatorio e irrecuperable; no se expone secreto. Un email ya usado por un `Mayorista` *real* (no espejo) del mismo tenant no se reutiliza. El espejo **no** consume cuota mensual de mayorista (OQ-5, propuesta de este modelo). ADR-019: se extiende/reutiliza `Mayorista`; no se crea un `User` paralelo. |
| **ServiceClient** (existente, actor del sistema) | `id`, `system`, `secret_hash`, `tenant_id`, `is_active` | Identidad del backend llamante. Credenciales ausentes, inválidas, cliente inactivo o tenant inactivo → fail-closed; no se crea ni se revela existencia de recursos. Aporta `system` y `tenant_id` a todas las operaciones. |
| **Tenant** (existente, referenciada) | `id`, estado activo | Un solo tenant comercial en V1, pero el aislamiento por `tenant_id` no se relaja (ADR-012). |
| **Prenda** (existente, referenciada, opcional) | `id`, `mayorista_id` | Si se envía al crear el vínculo, debe pertenecer al mayorista resuelto. No se crea ni se muta en este contexto. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| **ExternalProductId** | texto | Obligatorio; 1..255 caracteres. Identifica el producto borrador en BFashion. No implica propiedad. |
| **ExternalStaffId** | texto | Obligatorio. PK de `django.contrib.auth.User` transportada como string para no acoplarse al tipo entero de BFashion. Igualdad por valor. |
| **ExternalWholesalerId** | texto opcional | Si el vínculo existente ya lo tiene y el valor nuevo difiere, la creación se rechaza (coherente con `resolve_active_link`). |
| **StaffRole** | `admin` \| `owner` \| `staff` | Conjunto cerrado = `STAFF_ROLES`. Cualquier otro valor es inválido: el espejo no serviría para autorizar. Defecto de aprovisionamiento: `staff`. |
| **SystemName** | texto | Identidad del sistema llamante. Solo del `ServiceClient`. |
| **TenantId** | UUID | Solo del `ServiceClient`. Nunca del cuerpo. |
| **StaffId** | UUID | Identidad interna del `Mayorista` espejo. Es lo que BFashion aserta después como `staff_id`. |
| **EmailAddress** | email | Obligatorio al aprovisionar. Formato válido. Colisión con un `Mayorista` real del mismo tenant = conflicto de dominio. |
| **DisplayName** | texto | Nombre visible del staff; no se sincroniza en V1 tras el alta. |
| **LinkActivity** | `active` \| `inactive` | Un `ProductLink` inactivo no se reactiva al crear. Un `StaffIdentityLink` inactivo sí se reactiva al reaprovisionar (asimetría intencional: el espejo es la misma persona; el vínculo de producto desactivado es otra operación). |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| **ProductLink** | Referencias a `Mayorista`, `Prenda?`, `Tenant`; `created_by` → `StaffId` | (1) Unicidad global `(system, external_product_id)`. (2) `system`/`tenant_id` inmutables y derivados del cliente. (3) `mayorista_id` nace de la identidad de staff vigente, no del id externo. (4) Crear es idempotente: misma tupla + mismo contenido → la misma fila, `created = false`. (5) Crear no reactiva. (6) Colisión de unicidad con otro tenant → rechazo sin mutación. (7) `prenda_id` ajeno → rechazo sin alta. (8) `external_wholesaler_id` distinto del persistido → rechazo. |
| **StaffIdentityLink** | Referencia al `Mayorista` espejo que este agregado *dio de alta* | (1) Unicidad `(system, external_staff_id)`. (2) Cardinalidad 1:1 con el espejo: nunca un segundo `Mayorista`. (3) El espejo cumple `STAFF_ROLES` y el tenant del cliente. (4) Revocar no elimina espejo ni historia (`publication_selections.selected_by`, `product_links.created_by`). (5) Reaprovisionar tras revocar reactiva el mismo `staff_id`. (6) Email de un mayorista real del mismo tenant no se secuestra. (7) El espejo no computa cuota mensual. (8) Revocar no cancela photoshoots en curso; solo bloquea *nuevas* operaciones que pasen por `resolve_staff_identity`. |

`Mayorista` y `ServiceClient` siguen siendo raíces de sus contextos. Este bolt *usa* esas raíces; no las rediseña. El alta del espejo es un efecto colateral controlado del agregado `StaffIdentityLink`.

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| **ProductLinkCreated** | Primera persistencia de un vínculo activo | `product_link_id`, `system`, `external_product_id`, `mayorista_id`, `tenant_id`, `created_by` |
| **ProductLinkCreationReplayed** | Misma tupla única, mismo contenido, vínculo activo | `product_link_id`, `created = false` |
| **ProductLinkCreationRejected** | Invariante violado (tenant ajeno, staff inválido, prenda ajena, vínculo inactivo, wholesaler distinto) | `system`, `external_product_id`, `reason` |
| **StaffIdentityProvisioned** | Primera persistencia de vínculo + espejo | `staff_identity_link_id`, `external_staff_id`, `staff_id`, `tenant_id`, `role` |
| **StaffIdentityReplayed** | Reaprovisionar un vínculo ya activo | `staff_id` (el mismo), `created = false` |
| **StaffIdentityReactivated** | Reaprovisionar un vínculo previamente revocado | `staff_id` (el mismo), `is_active = true`, `revoked_at = null`, `created = false` |
| **StaffIdentityRevoked** | Revocación lógica (también si ya estaba revocado: evento idempotente / no-op observable) | `staff_id`, `external_staff_id`, `is_active = false`, `revoked_at` |
| **StaffIdentityResolutionDenied** | `staff_id` asertado desconocido, revocado, sin rol, o de otro tenant | `staff_id`, `tenant_id`, `reason` |

Estos eventos documentan el lenguaje del dominio. V1 no exige un bus: bastan persistencia + logs estructurados sin secretos (NFR-6).

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| **ProductLinkProvisioningService** (extiende el servicio de resolución existente; no lo sustituye) | `create_link(client, external_product_id, staff_id, external_wholesaler_id?, prenda_id?) → (ProductLink, created)` | `StaffIdentityService.resolve_staff_identity`, `ProductLinkRepository`, `PrendaRepository` (solo verificación de pertenencia) |
| **StaffIdentityService** | `provision(client, external_staff_id, email, display_name, role) → (StaffIdentityLink, staff_id, created)`; `revoke(client, external_staff_id) → StaffIdentityLink`; `resolve_staff_identity(client, staff_id) → Mayorista` | `StaffIdentityLinkRepository`, `MayoristaRepository` |
| **ServiceAuthentication** (existente, no se modifica) | Verifica `X-Service-Id` / `X-Service-Secret` fail-closed y entrega el `ServiceClient` | `ServiceClientRepository` |

Reglas de servicio:

- `create_link` exige un `staff_id` que `resolve_staff_identity` acepte. Un staff desconocido, revocado, sin rol o de otro tenant no crea nada.
- `provision` es la primera historia del intent: no depende de `ProductLink`.
- `resolve_staff_identity` es el **único** punto donde el puente decide vigencia del staff. El resto de endpoints del contrato C (este bolt y los siguientes) deben pasar por aquí, no reimplementar la regla. `_authorize_staff` existente se satisface con el espejo; no se reescribe.
- Idempotencia de alta: la restricción única es la autoridad (patrón ADR-054 / ADR-010). Una colisión concurrente no es un error 500: se relee la fila existente y se decide `created = false` o rechazo de invariante.
- Fail-closed: credenciales inválidas no distinguen si el producto o el staff existen.

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| **ProductLinkRepository** (existente, se extiende) | `ProductLink` | `get_by_system_and_external_product(system, external_product_id)`; `add(link)`; las resoluciones ya existentes (`resolve_active_link`, `resolve_owned_link`) no cambian de contrato |
| **StaffIdentityLinkRepository** (nuevo) | `StaffIdentityLink` | `get_by_system_and_external_staff(system, external_staff_id)`; `get_active_by_mayorista(system, tenant_id, mayorista_id)`; `add(link)`; `save(link)` |
| **MayoristaRepository** (existente) | `Mayorista` | `get_by_id`; `get_by_email_and_tenant`; `add(mayorista)` — el espejo se da de alta aquí; no se borra nunca desde este contexto |
| **ServiceClientRepository** (existente, solo lectura) | `ServiceClient` | Resolución que ya usa la dependencia de autenticación de servicio |
| **PrendaRepository** (existente, solo lectura) | `Prenda` | Verificar `prenda.mayorista_id == link.mayorista_id` cuando el alta trae `prenda_id` |

La unicidad `(system, external_*_id)` vive en el repositorio/esquema, no solo en el servicio. El servicio captura la colisión y la traduce a replay o rechazo.

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Puente** | API servidor-a-servidor Virtual Closet ↔ BFashion. Este bolt cubre el alta de identidad y de vínculo del contrato C. |
| **ServiceClient** | Identidad del backend llamante. Única fuente de `system` y `tenant_id`. |
| **Fail-closed** | Ante duda (credencial, tenant, staff, vínculo, prenda) se rechaza y no se muta. No se filtra existencia a un cliente no autenticado. |
| **Vínculo / ProductLink** | Mapeo autorizado y persistido producto externo → propietario en Virtual Closet. La propiedad no se infiere. |
| **Producto borrador** | Producto que BFashion crea primero; su id es el `external_product_id` del vínculo. |
| **Identidad de staff espejo** | Par `StaffIdentityLink` + `Mayorista` que representa a un usuario de BFashion dentro de Virtual Closet. |
| **Espejo** | La fila `Mayorista` del par. Actor reconocible por `_authorize_staff`; no es una cuenta con la que se inicie sesión. |
| **Mayorista real** | `Mayorista` que no es espejo: cuenta usable del tenant. Su email no puede secuestrarse para un espejo. |
| **staff_id** | UUID del espejo. Lo aserta BFashion en cada llamada del puente. |
| **external_staff_id** | Id del usuario en BFashion, como texto. |
| **Aprovisionar** | Crear o devolver el espejo de forma idempotente. |
| **Revocar** | Desactivar el vínculo de identidad sin borrar historia. Bloquea operaciones *nuevas*, no cancela las en curso. |
| **Reactivar** | Reaprovisionar un espejo revocado: mismo UUID, `is_active = true`. Distinto de reactivar un `ProductLink`. |
| **created** | Bandera de replay: `true` solo en el alta real; `false` en idempotencia o reactivación. |
| **STAFF_ROLES** | Conjunto cerrado `{admin, owner, staff}` que `_authorize_staff` ya exige. |
| **Contrato C** | Superficie nueva del intent 009. Este bolt entrega `product-links` y `staff-identities`. |
| **Intent hermano** | `020-ai-product-imagery-integration` (BFashion). Consume estos contratos; no se implementa aquí. |

## Decisiones de dominio que condicionan el diseño

1. **Simetría ProductLink / StaffIdentityLink.** Misma forma de unicidad, mismo `tenant_id`, mismo `is_active`. El código y el esquema deben verse paralelos a propósito.
2. **Asimetría de reactivación.** Crear un `ProductLink` no reactiva. Reaprovisionar un `StaffIdentityLink` sí. El staff es la misma persona; un vínculo de producto desactivado es una operación distinta y fuera de alcance.
3. **Un solo punto de vigencia.** `resolve_staff_identity` concentra «¿este `staff_id` puede operar ahora?». Revocar solo tiene efecto si todo el contrato C pasa por ahí.
4. **OQ-5 (propuesta de este modelo): los espejos no computan cuota.** El espejo no es un mayorista comercial. Si computara `LimiteMensualAlcanzadoError`, aprovisionar N staff agotaría un límite pensado para mayoristas reales.
5. **OQ-2 no bloquea el modelo.** La forma (`external_staff_id` string, idempotencia por `(system, external_staff_id)`, revocación `:revoke`) está fijada en FR-2. La confirmación cruzada con el intent 020 es de contrato, no de lenguaje de dominio.
6. **Idempotencia concurrente.** Dos altas simultáneas del mismo par único: una persiste, la otra relee. Ninguna es un error de integridad visible.
7. **Taxonomía de rechazo** (HTTP exacto en Stage 2; aquí el significado):
   - Cliente de servicio ausente/inválido → no autenticado
   - `staff_id` asertado inválido o revocado → no autorizado
   - Par único de producto ya de otro tenant → conflicto de autorización, sin mutación
   - `external_staff_id` desconocido al revocar → no encontrado en el alcance del cliente
   - Espejo de otro tenant al revocar → no encontrado o no autorizado; **sin filtrar existencia cross-tenant** (espíritu ADR-040)
   - Email de mayorista real → conflicto
   - `role` u `email` / `external_product_id` mal formados → invariante de valor
8. **Sin secreto en el modelo de respuesta.** El agregado nunca expone `password_hash`, secreto de servicio ni material de credencial.

## Story Coverage

| Story | Cubierta por |
|-------|----------------|
| **001-product-link-creation** | Agregado `ProductLink`; `ProductLinkProvisioningService.create_link`; VOs `ExternalProductId`, `ExternalWholesalerId`; eventos de alta / replay / rechazo; invariantes de tenant, staff, prenda e idempotencia |
| **002-staff-identity-provisioning** | Agregado `StaffIdentityLink`; `StaffIdentityService.provision`; VOs `ExternalStaffId`, `StaffRole`, `EmailAddress`; espejo `Mayorista`; OQ-5; evento de alta / replay / reactivación |
| **003-staff-identity-revocation** | `StaffIdentityService.revoke` + `resolve_staff_identity`; invariante de no-borrado; evento `StaffIdentityRevoked`; fotoshoot en curso fuera del efecto de la revocación |

## Prior Decisions Applied

- **ADR-012** (aislamiento multi-capa): `tenant_id` siempre del `ServiceClient`; ninguna consulta nueva relaja el alcance.
- **ADR-019**: el espejo es un `Mayorista`, no un `User` nuevo.
- **ADR-001**: el espejo no abre un contexto de autenticación usable; no es login.
- **ADR-054 / ADR-010**: la unicidad en persistencia es la autoridad de la idempotencia; el servicio traduce la colisión.
- **ADR-040**: al revocar, no filtrar existencia de identidades de otro tenant.
- **ADR-051** no aplica: aquí no hay visibilidad staff-vs-admin de plantillas; el aislamiento es tenant + `ServiceClient`.

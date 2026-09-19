---
unit: 001-bridge-provisioning
bolt: 050-bridge-provisioning
stage: design
status: complete
updated: 2026-09-19T00:37:52Z
---

# Technical Design - bridge-provisioning

## Architecture Pattern

**Layered DDD dentro del monolito FastAPI**, el patrón del proyecto (`api/routers → services → repositories → models`).

No se introduce un bounded context hexagonal nuevo ni un router paralelo. El puente S2S ya vive en `integration`; este bolt **extiende** esa superficie y añade un agregado simétrico a `ProductLink`.

Razones:

- El `ServiceClient` y `get_service_client` ya son el borde de autenticación del contrato B y C.
- `ProductLinkService` ya resuelve vínculos; aquí solo se añade `create_link` idempotente.
- `_authorize_staff` / `STAFF_ROLES` son un contrato congelado: el espejo se fabrica para satisfacerlos, no al revés. **No se modifica** `integration_service.py`.
- La vigencia del espejo (revocado o no) es una regla *nueva* del contrato C. Se concentra en un servicio nuevo para que 051/053/056 no la reimplementen.

## Layer Structure

```text
┌─────────────────────────────────────────────────────────────┐
│ Presentation                                                │
│   api/routers/integration.py     3 endpoints nuevos         │
│   api/schemas/integration.py     DTOs de alta / revocación  │
├─────────────────────────────────────────────────────────────┤
│ Application                                                 │
│   services/product_link_service.py     + create_link        │
│   services/staff_identity_service.py   provision/revoke/    │
│                                        resolve (NUEVO)      │
├─────────────────────────────────────────────────────────────┤
│ Domain                                                      │
│   models/product_link.py           sin cambio de contrato   │
│   models/staff_identity_link.py    NUEVO                    │
│   excepciones de dominio en services/                       │
├─────────────────────────────────────────────────────────────┤
│ Infrastructure                                              │
│   repositories/product_link_repo.py          + get_by_pair  │
│   repositories/staff_identity_link_repo.py   NUEVO          │
│   repositories/mayorista_repo.py             reutilizado    │
│   alembic/versions/*_staff_identity_links.py NUEVO          │
└─────────────────────────────────────────────────────────────┘
```

Responsabilidades por capa:

- **Router**: `Depends(get_service_client)`, traduce excepciones de dominio → HTTP, no contiene reglas.
- **Service**: invariantes, idempotencia, transacción Mayorista+vínculo, composición de vigencia.
- **Repository**: lookups por par único, insert, save. Sin reglas de negocio.
- **Model**: mapeo ORM + unicidad. `system`/`tenant_id` no se aceptan del cuerpo en el schema.

## Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Model | `models/staff_identity_link.py` | ORM `StaffIdentityLink`, unicidad `(system, external_staff_id)` |
| Model | `models/product_link.py` | Sin cambio de columnas ni de invariante documentado |
| Repository | `repositories/staff_identity_link_repo.py` | `get_by_system_and_external_staff`, `get_active_by_mayorista`, `add`, `save` |
| Repository | `repositories/product_link_repo.py` | Añadir `get_by_system_and_external_product` si no existe; el resto intacto |
| Service | `services/staff_identity_service.py` | `provision`, `revoke`, `resolve_staff_identity` |
| Service | `services/product_link_service.py` | `create_link` idempotente; no tocar `resolve_active_link` / `resolve_owned_link` |
| Schema | `api/schemas/integration.py` | Request/response de los 3 endpoints; `extra = "ignore"` |
| Router | `api/routers/integration.py` | Registrar las 3 rutas bajo `/api/integration/v1` |
| Auth | `core/dependencies.py` `get_service_client` | Reutilizado, sin cambios |
| Const | `integration_service.STAFF_ROLES` | Solo lectura; no se edita el módulo |

## API Design

Base: `/api/integration/v1`. Auth: cabeceras `X-Service-Id` + `X-Service-Secret`. Sin cookie.

Los schemas **no declaran** `system` ni `tenant_id`. Si el cliente los envía, Pydantic `extra = "ignore"` los descarta. El servicio toma ambos del `ServiceClient`.

### POST `/api/integration/v1/product-links`

Crea o devuelve el vínculo explícito.

**Request**

```json
{
  "external_product_id": "string, 1..255",
  "external_wholesaler_id": "string | null",
  "staff_id": "uuid",
  "prenda_id": "uuid | null"
}
```

**Response 201** (alta real) / **200** (replay idempotente)

```json
{
  "product_link_id": "uuid",
  "external_product_id": "string",
  "mayorista_id": "uuid",
  "tenant_id": "uuid",
  "is_active": true,
  "created": true
}
```

`mayorista_id` = `StaffIdentityLink.mayorista_id` del `staff_id` resuelto (el espejo), no un mayorista comercial distinto.

### POST `/api/integration/v1/staff-identities`

Aprovisiona o reactiva el espejo. Consumidor previsto: `manage.py link_staff_identity` (intent 020). Forma fijada en FR-2 (OQ-2 no bloquea).

**Request**

```json
{
  "external_staff_id": "string",
  "email": "email",
  "display_name": "string",
  "role": "staff"
}
```

`role` enum `admin | owner | staff`; default `"staff"`.

**Response 201** / **200**

```json
{
  "staff_id": "uuid",
  "external_staff_id": "string",
  "email": "string",
  "role": "staff",
  "is_active": true,
  "created": true
}
```

`created` es `false` tanto en replay de un vínculo activo como en reactivación de uno revocado. Nunca viaja `password`, hash ni secreto.

### POST `/api/integration/v1/staff-identities/{external_staff_id}:revoke`

Revocación lógica, idempotente.

**Request**: cuerpo vacío. `external_staff_id` en path (string; URL-encoded).

**Response 200**

```json
{
  "staff_id": "uuid",
  "external_staff_id": "string",
  "is_active": false
}
```

## Data Persistence

### Tabla nueva `staff_identity_links`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `system` | VARCHAR | NOT NULL |
| `external_staff_id` | VARCHAR | NOT NULL |
| `mayorista_id` | UUID | NOT NULL, FK → `mayoristas.id` ON DELETE RESTRICT |
| `tenant_id` | UUID | NOT NULL, FK → `tenants.id` |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |
| `revoked_at` | TIMESTAMPTZ | NULL |

Índices:

- `uq_staff_identity_links_system_external_staff` UNIQUE (`system`, `external_staff_id`)
- `ix_staff_identity_links_tenant_mayorista` (`tenant_id`, `mayorista_id`) — resolución por `staff_id`
- `ix_staff_identity_links_tenant_active` (`tenant_id`, `is_active`)

Simetría deliberada con `product_links`: misma forma de unicidad, mismo `tenant_id`, mismo `is_active`.

### Tabla existente `product_links`

Sin migración de columnas. `create_link` se apoya en `uq_product_links_system_external_product`. `created_by` = `staff_id` autorizado.

### Tabla existente `mayoristas`

Sin columnas nuevas (ADR-019: no crear `User`). El alta del espejo inserta una fila:

- `email` = email del request
- `role` = `StaffRole` validado
- `tenant_id` = `ServiceClient.tenant_id`
- `password_hash` = hash de un secreto aleatorio irrecuperable (p. ej. `secrets.token_urlsafe(32)` pasado por el hasher existente)
- No se devuelve el secreto

La señal «este mayorista es un espejo» es la existencia de `staff_identity_links.mayorista_id`. No se añade `is_bridge_mirror` en este bolt.

### Migración Alembic

Una revisión de esquema (no data migration). Convención secuencial del repo. Downgrade: `DROP TABLE staff_identity_links`. No hay backfill.

## Use-case flows

### `create_link`

1. Autenticar `ServiceClient` (router). Fail-closed → 401.
2. `staff = StaffIdentityService.resolve_staff_identity(client, staff_id)`.
3. Si `prenda_id`: verificar pertenencia al `staff.id`. Si no → `PrendaForbiddenError`.
4. `existing = ProductLinkRepo.get_by_system_and_external_product(client.system, external_product_id)`.
5. Si existe:
   - `existing.tenant_id != client.tenant_id` → `CrossTenantLinkError` (403, sin mutar).
   - `existing.is_active is False` → `InactiveLinkError` (409).
   - `external_wholesaler_id` informado y distinto del persistido → `WholesalerMismatchError` (403).
   - En otro caso → devolver existing, `created=False`, HTTP 200.
6. Si no existe: construir `ProductLink` con `system`/`tenant_id` del cliente, `mayorista_id=staff.id`, `created_by=staff.id`. `add` + flush.
7. `IntegrityError` por la unicidad: rollback parcial del insert, releer, repetir el paso 5. Nunca 500.

### `provision`

1. Autenticar cliente.
2. Validar `role ∈ STAFF_ROLES` y email (Pydantic + chequeo de servicio).
3. `existing = StaffIdentityLinkRepo.get_by_system_and_external_staff(...)`.
4. Si existe y `existing.tenant_id != client.tenant_id` → 403/404 sin mutar (no filtrar al otro tenant: responder como no autorizado / no encontrado genérico; ver errores).
5. Si existe y está activo → 200, mismo `staff_id`, `created=False`. No actualizar email/nombre/rol en V1 (fuera de alcance).
6. Si existe y está revocado → `is_active=true`, `revoked_at=null`, 200, mismo `staff_id`, `created=False`.
7. Si no existe:
   - Buscar `Mayorista` por `(email, tenant_id)`.
   - Si existe y **no** es el espejo de este `external_staff_id` → `MirrorEmailConflictError` (409). Incluye mayorista real y otro espejo.
   - Si no existe: crear `Mayorista` espejo + `StaffIdentityLink` en **la misma transacción**.
8. `IntegrityError` en el par único: releer y tratar como 5 o 6. Nunca dos espejos.

### `revoke`

1. Autenticar cliente.
2. Buscar por `(client.system, external_staff_id)`.
3. Ausente → `StaffIdentityNotFoundError` (404). No se busca en otros `system` ni se revela si existe en otro tenant.
4. `link.tenant_id != client.tenant_id` → misma 404 (ADR-040: sin oráculo de existencia).
5. Si ya inactivo → 200 idempotente, mismos campos.
6. Si activo → `is_active=false`, `revoked_at=now()`, 200. **No** `DELETE` de `Mayorista`.

### `resolve_staff_identity` (punto único de vigencia del contrato C)

Usado por `create_link` en este bolt y, a partir de 051/053, por el resto de C.

1. Cargar `Mayorista` por `staff_id`. Ausente → `StaffForbiddenError`.
2. `mayorista.tenant_id != client.tenant_id` → `StaffForbiddenError`.
3. `mayorista.role ∉ STAFF_ROLES` → `StaffForbiddenError`.
4. Cargar `StaffIdentityLink` activo por `(client.system, client.tenant_id, mayorista.id)`. Ausente o `is_active=false` → `StaffForbiddenError`.

Así, un espejo revocado sigue existiendo como `Mayorista` y `_authorize_staff` *podría* aceptarlo en el contrato B (fuera de este alcance), pero **todo endpoint nuevo de C** que pase por `resolve_staff_identity` lo rechaza con 403.

No se llama a `_authorize_staff` (puede ser privado). Se importa **solo** la constante `STAFF_ROLES`. `integration_service.py` no se edita.

## Security Design

| Concern | Approach |
|---------|----------|
| Autenticación de servicio | `get_service_client` existente; bcrypt del secreto; cliente y tenant activos. Ausente/inválido → 401, mismo cuerpo, sin revelar si el recurso existe |
| Autorización de staff | `resolve_staff_identity` (rol + tenant + vínculo activo). No cookie, no JWT de mayorista |
| Tenant isolation | `system`/`tenant_id` solo del `ServiceClient`. Lookups de unicidad comprueban tenant antes de mutar. Listener ADR-012 sigue aplicando |
| Cross-tenant revoke | 404 genérico, no 403 que confirme existencia (ADR-040) |
| Cross-tenant product link | 403 sin mutación (criterio explícito de la historia 001: el caller ya conoce el `external_product_id`) |
| Secretos | Hash irrecuperable en el espejo. Respuesta y logs sin password, hash, `X-Service-Secret`, ni material de credencial (NFR-6) |
| Fail-closed | Cualquier duda (staff, prenda, tenant, unicidad ajena) rechaza y no escribe |
| Input | Pydantic: longitudes, `EmailStr`, UUID, enum de rol. Path `external_staff_id` como string |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| NFR-1 latencia p95 ≤ 1 s / 10 concurrentes | Rutas síncronas, 1–3 lookups por índice único, sin I/O externo ni Celery. La colisión concurrente es un retry de lectura, no un lock largo |
| NFR-6 aislamiento y secretos | Ver Security. Tests de contrato: 401/403/404/409 y ausencia de secretos en body |
| Idempotencia concurrente | Autoridad = UNIQUE en Postgres (ADR-054 / ADR-010). `IntegrityError` → releer |
| Durabilidad | Una transacción por alta de espejo (Mayorista + link). Revocar es un UPDATE |
| Escalabilidad | Volumen: 1 fila por staff / producto de BFashion. Sin caché. Índices arriba |
| Cuota (OQ-5) | Este bolt no llama a `prenda_service` ni a límites mensuales. El espejo no computa cuota. Bolts posteriores que usen `product_link.mayorista_id` deben excluir ids presentes en `staff_identity_links` |

## Error Handling

Excepciones de dominio en `services/` → `HTTPException` / error estructurado en el router.

Forma: `{"detail": {"code": "...", "message": "...", "context": {}}}` para dominio; `{"detail": "..."}` para 401 simple.

| Error Type | HTTP | Code | Response |
|------------|------|------|----------|
| Cabeceras ausentes/inválidas, cliente o tenant inactivo | 401 | — | `{"detail": "Unauthorized"}` — idéntico en todos los casos |
| Staff desconocido, sin rol, otro tenant, o revocado (asserción) | 403 | `STAFF_FORBIDDEN` | sin crear vínculo |
| `external_product_id` de otro tenant | 403 | `PRODUCT_LINK_TENANT_CONFLICT` | sin mutar |
| `prenda_id` de otro mayorista | 403 | `PRODUCT_LINK_PRENDA_FORBIDDEN` | sin crear |
| `external_wholesaler_id` distinto del persistido | 403 | `PRODUCT_LINK_WHOLESALER_MISMATCH` | sin mutar |
| Vínculo existente `is_active=false` | 409 | `PRODUCT_LINK_INACTIVE` | motivo explícito; no reactivar |
| Email de un `Mayorista` real u otro espejo | 409 | `STAFF_EMAIL_CONFLICT` | motivo explícito |
| `external_staff_id` desconocido o de otro tenant al revocar | 404 | `STAFF_IDENTITY_NOT_FOUND` | cuerpo genérico |
| `external_product_id` vacío/>255, email malformado, `role` fuera de set | 422 | validación Pydantic | FastAPI default |

401 no usa código de dominio rico: no se filtra si el producto o el staff existen.

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| BFashion (intent 020) | Consume los 3 endpoints; persiste `staff_id` en `StaffIntegrationIdentity` | REST S2S; contrato C. Este repo no implementa el cliente |
| PostgreSQL | Persistencia de vínculos e identidades | SQLAlchemy async |
| `get_service_client` | Auth fail-closed | Dependencia FastAPI existente |
| `MayoristaRepository` | Alta y lectura del espejo | Interno |
| `STAFF_ROLES` | Contrato de rol aceptable | Import de constante; sin editar `integration_service.py` |
| `GET /api/product-links/lookup` y `scripts/link_product.py` | Fuera de alcance | No se tocan |

## Transaction & concurrency

- `provision` (alta): `Mayorista` + `StaffIdentityLink` en un solo `commit`. Si el unique salta, no queda un `Mayorista` huérfano: o se hace el insert del link en la misma transacción, o se aborta todo. Si dos requests crean el mismo email a la vez, el unique de email de `mayoristas` (si existe) o el unique del link decide; el perdedor relee o responde 409.
- `create_link`: un insert; unique → releer.
- `revoke`: un update; dos revokes concurrentes convergen en `is_active=false`.
- No Redis, no lease. No hay I/O de proveedor.

## Logging

`core/logger.py`, estructurado:

- info: `product_link_created|replayed`, `staff_identity_provisioned|replayed|reactivated|revoked` con ids, `system`, `tenant_id`, `created`
- warn: rechazos de invariante (código de error, no PII de más)
- never: secretos, password_hash, cabecera `X-Service-Secret`, cuerpos completos con email si el logger de prod ya redacta PII — el email puede ir en `debug` no en `info`

## Testing plan (contrato; ejecución en Stage 5)

- 201/200 idempotente product-link (mismo id, `created` correcto)
- 403 tenant ajeno, staff inválido/revocado, prenda ajena, wholesaler mismatch
- 409 vínculo inactivo
- 401 sin cabeceras
- 422 validación
- Dos concurrentes mismo `external_product_id` → sin 500
- Provision 201/200 mismo UUID; role ∈ STAFF_ROLES; tenant del cliente
- Respuesta sin material de credencial
- 409 email de mayorista real
- Revocar → 200 `is_active=false`; segundo revoke 200; `Mayorista` sigue existiendo
- Tras revoke, `create_link` con ese `staff_id` → 403
- Revocar desconocido → 404; otro tenant → 404
- Reactivar tras revoke → mismo `staff_id`, `created=false`

## Out of scope (reafirmado)

- Modificar `integration_service.py`, cookie login del espejo, sync de perfil, reactivar `ProductLink`, listar vínculos, cancelar photoshoots, cuota en `prenda_service` (solo la regla documentada).

## ADR candidates (Stage 3)

Decisiones que pueden merecer ADR, a presentar en la siguiente etapa:

1. Vigencia del staff de C en un servicio nuevo, sin tocar `_authorize_staff`
2. Idempotencia de alta gobernada por UNIQUE + releer (no `SELECT` previo como autoridad)
3. Espejos sin columna extra en `mayoristas`; la membresía en `staff_identity_links` es la señal
4. 404 (no 403) al revocar identidades de otro tenant

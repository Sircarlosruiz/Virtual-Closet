---
unit: 002-source-image-intake
intent: 009-bfashion-generation-bridge
phase: inception
status: draft
unit_type: backend
default_bolt_type: ddd-construction-bolt
created: 2026-09-18T09:50:00Z
updated: 2026-09-18T09:50:00Z
---

# Unit Brief: source-image-intake

## Purpose

Cerrar G1, el hueco central del intent: hoy no existe ninguna forma de que BFashion entregue bytes a Virtual Closet. `ImageGenerationRequest` solo acepta UUIDs de media que **ya vive** en Virtual Closet (`garment_id`, `model_id`, `reference_image_ids`) y todos los endpoints de subida (`/api/prendas/upload`, `/api/media/garments`, `/api/media/models`, `/api/tryoff/source-images`) son cookie-auth.

Esta unidad entrega una URL presignada por el puente, deja que el navegador del staff suba directo al almacenamiento de Virtual Closet, y después verifica el objeto real y lo registra como media utilizable. Los bytes no atraviesan el backend de BFashion ni el de Virtual Closet.

## Scope

### In Scope
- `POST /api/integration/v1/products/{external_product_id}/source-images:presign`
- `POST /api/integration/v1/products/{external_product_id}/source-images/{source_image_id}:confirm`
- Nuevo modelo `BridgeSourceImage` (ciclo `pending → ready | rejected`) y su revisión Alembic
- Servicio de admisión que delega el registro definitivo en los servicios de media existentes
- Validación previa a la firma (tipo, tamaño, `kind`) y verificación posterior del objeto real
- Rechazos fail-closed: vínculo ajeno, staff revocado, objeto inexistente, discrepancia declarado/real

### Out of Scope
- Camino multipart de respaldo: decisión explícita del dueño del producto (subida directa o nada)
- Reemplazo de los endpoints cookie-auth existentes, que siguen funcionando igual
- Transformaciones de imagen (recorte, reescalado, conversión de formato)
- Miniaturas y biblioteca de media para navegación
- Configuración de CORS y del endpoint público de MinIO: es despliegue, no código

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-3 | Solicitud de subida presignada por el puente | Must |
| FR-4 | Confirmación y registro de la imagen de origen | Must |
| FR-15 | Fail-closed transversal en todo el puente | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `BridgeSourceImage` (**nuevo**) | Reserva de subida por el puente y su ciclo de vida | `id`, `product_link_id`, `staff_id`, `kind` (`garment_on_model` \| `flat_garment`), `storage_key`, `declared_content_type`, `declared_size_bytes`, `actual_content_type`, `actual_size_bytes`, `status` (`pending` \| `ready` \| `rejected`), `rejection_reason`, `registered_media_id`, `registered_media_kind`, `tenant_id`, `created_at`, `confirmed_at` |
| `SourceImage` (existente, `models/tryoff_job.py`) | Media de origen del pipeline TryOff | Destino del registro cuando `kind = garment_on_model` |
| `GarmentPhoto` (existente, `models/media.py`) | Foto de prenda del pipeline VTON | Destino del registro cuando `kind = flat_garment` |
| `ProductLink` (existente) | Ancla de propiedad de la imagen de origen | — |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `presign_source_image` | Valida, reserva la fila y firma el `PUT` | `ServiceClient`, `external_product_id`, `staff_id`, `kind`, `content_type`, `size_bytes`, `filename` | `source_image_id`, `upload_url`, `storage_key`, `expires_in` |
| `confirm_source_image` | Verifica el objeto real y registra la media | `ServiceClient`, `external_product_id`, `source_image_id`, `staff_id`, `checksum?` | `BridgeSourceImage` en `ready` + media registrada |
| `reject_source_image` | Marca la reserva como `rejected` con motivo | motivo medido | `BridgeSourceImage` en `rejected` |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 3 |
| Must Have | 3 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| `001-source-image-presign` | Emitir la URL presignada de subida | Must | Planned |
| `002-source-image-confirm` | Confirmar y registrar la imagen de origen | Must | Planned |
| `003-source-image-rejection` | Rechazar subidas inválidas o ajenas | Must | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `001-bridge-provisioning` | El presign se resuelve contra un `ProductLink` que debe poder crearse por API, y el `staff_id` debe estar vigente |

### Depended By

| Unit | Reason |
|------|--------|
| `003-photoshoot-orchestration` | El disparo exige un `source_image_id` en estado `ready` |

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| MinIO / S3 | Firma del `PUT`, verificación del objeto (`object_exists`, `head_object`) | Medio — el endpoint público debe ser alcanzable por el navegador del staff |
| Navegador del staff | Ejecuta el `PUT` presignado | Medio — sin camino alternativo por decisión de producto |

---

## Technical Context

### Suggested Technology

Reutilizar el precedente que ya existe en este repositorio: `GET /api/prendas/upload-url` + `POST /api/prendas` (`api/routers/prendas.py`), apoyado en `StorageService.generate_upload_url` y `StorageService.object_exists`. No se introduce un mecanismo de almacenamiento nuevo.

El registro definitivo delega en los servicios de media existentes según el `kind`, para no crear un cuarto almacén paralelo de imágenes de origen:
- `garment_on_model` → `tryoff_source_image_service` (`SourceImage`), que es la entrada del pipeline TryOff
- `flat_garment` → `media_service` / `MediaUploadService` (`GarmentPhoto`), que es la entrada directa de VTON

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| `StorageService.generate_upload_url` | Firma del `PUT` | S3 presigned |
| `StorageService.object_exists` | Verificación del objeto real | S3 `head_object` |
| `tryoff_source_image_service` | Registro de media para `garment_on_model` | Interno |
| `media_service` / `MediaUploadService` | Registro de media para `flat_garment` | Interno |
| `ProductLinkService.resolve_active_link` | Resolución fail-closed de propiedad | Interno |

### Data Storage

| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| `bridge_source_images` | SQL | Una fila por intento de subida | Permanente; las `pending` caducadas se pueden purgar |
| Bytes de origen | Objeto (bucket `originals`) | 1 archivo por producto, ≤ límite configurado | Permanente mientras exista el vínculo |

---

## Constraints

- Los bytes no pasan por ningún backend: solo `PUT` directo del navegador al almacenamiento.
- Solo `image/jpeg` e `image/png`. Tamaño máximo configurable; `media_service._validate_file` ya fija el precedente de 10 MB.
- La URL presignada solo autoriza `PUT` sobre la clave emitida, con TTL configurable (propuesta: 900 s).
- Una imagen `pending` no es utilizable para generar. Solo `ready` lo es.
- Una discrepancia entre lo declarado en el presign y el objeto real deja la imagen en `rejected`, nunca en `ready`.
- La respuesta jamás contiene credenciales de almacenamiento ni de proveedor de IA.
- Revisión Alembic obligatoria por el nuevo modelo.

---

## Success Criteria

### Functional
- [ ] Un `PUT` con la URL emitida sube el archivo sin tocar ningún backend
- [ ] `content_type` no admitido o `size_bytes` excesivo se rechazan **antes** de firmar
- [ ] Confirmar sin que el objeto exista responde `409`; la imagen sigue `pending` y admite reintento
- [ ] Un tipo o tamaño real distinto del declarado deja la imagen en `rejected` con motivo
- [ ] Confirmar dos veces una imagen `ready` devuelve el mismo `source_image_id` con `200`
- [ ] Una imagen de otro `product_link` responde `403` y no se registra
- [ ] Tras confirmar, la media queda registrada en el almacén correcto según `kind`

### Non-Functional
- [ ] p95 ≤ 1 s en presign y confirm, excluyendo la transferencia del archivo (NFR-1)
- [ ] La URL presignada caduca en el TTL configurado y no autoriza otras claves ni otras operaciones (NFR-6)
- [ ] Un `ServiceClient` de otro tenant no resuelve ni confirma estas imágenes (NFR-6)

### Quality
- [ ] Cobertura de código > 80 %
- [ ] Todos los criterios de aceptación cubiertos por pruebas
- [ ] Revisión de código aprobada

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| `051-source-image-intake` | ddd | 001, 002, 003 | Camino de subida S2S completo y fail-closed |

---

## Notes

El supuesto crítico de esta unidad es de despliegue, no de código: **el navegador del staff de BFashion tiene que alcanzar el endpoint público de MinIO/S3 de Virtual Closet**. El dueño del producto decidió explícitamente que, si ese supuesto no se cumple, se corrige el despliegue y no se añade un segundo camino en el código. Verificar `MINIO_PUBLIC_ENDPOINT` y la política CORS del bucket **antes** de empezar el bolt.

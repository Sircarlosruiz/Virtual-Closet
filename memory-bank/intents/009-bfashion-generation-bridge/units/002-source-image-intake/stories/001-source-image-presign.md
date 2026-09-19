---
id: 001-source-image-presign
unit: 002-source-image-intake
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:20:00.000Z
assigned_bolt: 051-source-image-intake
implemented: true
---

# Story: 001-source-image-presign

## User Story

**As a** backend de BFashion actuando en nombre de un staff
**I want** obtener una URL presignada para que el navegador del staff suba el archivo directamente al almacenamiento de Virtual Closet
**So that** los bytes no atraviesen ni mi backend ni el de Virtual Closet, y la subida de 5-10 MB no dependa de dos saltos HTTP

## Acceptance Criteria

- [ ] **Given** un vínculo activo y un `staff_id` vigente, **When** llamo a `POST /api/integration/v1/products/{external_product_id}/source-images:presign` con `kind`, `content_type`, `size_bytes` y `filename` válidos, **Then** recibo `201` con `source_image_id`, `upload_url`, `method: "PUT"`, `headers`, `expires_in` y `storage_key`
- [ ] **Given** la `upload_url` recibida, **When** el navegador ejecuta un `PUT` con esos `headers`, **Then** el objeto queda en el almacenamiento sin haber pasado por ningún backend
- [ ] **Given** un `content_type` fuera de `{image/jpeg, image/png}`, **When** solicito el presign, **Then** recibo `422` y **no se firma ninguna URL**
- [ ] **Given** un `size_bytes` por encima del límite configurado, **When** solicito el presign, **Then** recibo `422` y no se firma ninguna URL
- [ ] **Given** un `kind` distinto de `garment_on_model` o `flat_garment`, **When** solicito el presign, **Then** recibo `422`
- [ ] **Given** un presign concedido, **When** consulto la fila creada, **Then** está en estado `pending`, asociada al `product_link` resuelto y al `staff_id` autorizado, y **no es utilizable para generar**
- [ ] **Given** la `upload_url`, **When** intento usarla para una clave distinta o para un método distinto de `PUT`, **Then** el almacenamiento rechaza la operación
- [ ] **Given** un vínculo inexistente, inactivo, de otro tenant o de otro mayorista, **When** solicito el presign, **Then** recibo `404`/`403` y no se firma nada
- [ ] **Given** la respuesta completa, **When** la inspecciono, **Then** no contiene credenciales de almacenamiento ni de proveedor de IA

## Technical Notes

- Reutilizar `StorageService.generate_upload_url`, siguiendo el precedente `GET /api/prendas/upload-url` (`api/routers/prendas.py:72`). No introducir un mecanismo de almacenamiento nuevo.
- La clave se construye con un patrón determinista que incluye el `product_link_id` y el `source_image_id`, para que la propiedad sea legible desde la propia clave.
- TTL configurable, propuesta 900 s, coherente con el TTL de transferencia del contrato A.
- Bucket `originals`, igual que el resto de media de origen del proyecto.
- El límite de tamaño toma como referencia `media_service._validate_file` (10 MB).
- Verificar `MINIO_PUBLIC_ENDPOINT` y la política CORS del bucket antes de empezar: el navegador tiene que alcanzar ese endpoint y no hay camino alternativo por decisión de producto.

## Dependencies

### Requires
- `001-product-link-creation`

### Enables
- `002-source-image-confirm`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Se pide presign dos veces para el mismo producto | Se emiten dos reservas independientes; el photoshoot elige cuál usa por `source_image_id` |
| La URL caduca antes del `PUT` | El `PUT` falla en el almacenamiento; la fila sigue `pending` y se puede pedir un presign nuevo |
| `size_bytes` declarado no coincide con el archivo real | Se detecta en la confirmación, no aquí (ver `002` y `003`) |
| `filename` con caracteres no ASCII o con separadores de ruta | Se sanea; nunca llega crudo a la clave de almacenamiento |

## Out of Scope

- Subida multipart por el backend
- Transformaciones de imagen
- Miniaturas
- Purga de reservas `pending` caducadas

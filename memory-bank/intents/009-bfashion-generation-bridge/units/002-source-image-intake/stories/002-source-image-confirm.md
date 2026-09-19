---
id: 002-source-image-confirm
unit: 002-source-image-intake
intent: 009-bfashion-generation-bridge
status: complete
priority: must
created: 2026-09-18T10:22:00.000Z
assigned_bolt: 051-source-image-intake
implemented: true
---

# Story: 002-source-image-confirm

## User Story

**As a** backend de BFashion
**I want** confirmar que el archivo ya está subido y que Virtual Closet lo registre como media utilizable
**So that** pueda disparar un photoshoot con un `source_image_id` que de verdad tiene bytes detrás

## Acceptance Criteria

- [ ] **Given** un objeto ya subido con la URL presignada, **When** llamo a `POST .../source-images/{source_image_id}:confirm`, **Then** recibo `200` con `status: "ready"`, `kind`, `content_type`, `size_bytes` y `preview_url`
- [ ] **Given** una confirmación exitosa de `kind: garment_on_model`, **When** inspecciono la persistencia, **Then** la media quedó registrada mediante `tryoff_source_image_service` como `SourceImage`, entrada del pipeline TryOff
- [ ] **Given** una confirmación exitosa de `kind: flat_garment`, **When** inspecciono la persistencia, **Then** la media quedó registrada mediante `media_service` como `GarmentPhoto`, entrada directa de VTON
- [ ] **Given** una imagen ya en `ready`, **When** confirmo otra vez, **Then** recibo `200` con el mismo `source_image_id` y no se registra una segunda media
- [ ] **Given** un `source_image_id` cuyo objeto no existe en el almacenamiento, **When** confirmo, **Then** recibo `409` con código de error explícito, la imagen permanece `pending` y puedo reintentar tras subir
- [ ] **Given** una imagen en `ready`, **When** la referencio desde un photoshoot, **Then** es aceptada como entrada válida
- [ ] **Given** una imagen en `pending` o `rejected`, **When** la referencio desde un photoshoot, **Then** el disparo se rechaza con `422`
- [ ] **Given** un `checksum_sha256` enviado que no coincide con el objeto real, **When** confirmo, **Then** la imagen queda `rejected` con motivo y no se registra media

## Technical Notes

- Verificar existencia con `StorageService.object_exists`, y tipo y tamaño reales con la metadata del objeto (`head_object`). No fiarse de lo declarado en el presign: eso es exactamente lo que la historia `003` prueba.
- El registro delega en los servicios de media existentes según el `kind`. La intención es no crear un cuarto almacén paralelo de imágenes de origen: ya hay tres (`prenda`, `garment_photos`, `tryoff_source_images`).
- `registered_media_id` y `registered_media_kind` en `BridgeSourceImage` guardan a dónde fue a parar el registro, para que la orquestación sepa qué servicio consumir después.
- `preview_url` es una URL presignada de descarga de vida corta, nunca una clave expuesta como si fuese pública.
- La idempotencia de la confirmación es de estado, no de clave: si ya está `ready`, se devuelve lo mismo.

## Dependencies

### Requires
- `001-source-image-presign`

### Enables
- `001-photoshoot-submission`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Dos confirmaciones concurrentes de la misma imagen | Una registra la media, la otra devuelve el mismo resultado. Nunca dos medias registradas |
| El objeto existe pero está vacío (0 bytes) | `rejected` con motivo; se reutiliza la validación de `media_service` |
| El objeto es un PNG declarado como JPEG | Se registra el tipo real detectado; si contradice lo declarado, `rejected` con motivo (ver `003`) |
| Confirmar tras revocar el `staff_id` | `403`: la vigencia del staff se comprueba también aquí |

## Out of Scope

- Reintentar la subida automáticamente
- Conversión de formato
- Validación de contenido (que la foto sea realmente de una prenda)

---
id: 003-source-image-rejection
unit: 002-source-image-intake
intent: 009-bfashion-generation-bridge
status: draft
priority: must
created: 2026-09-18T10:24:00Z
assigned_bolt: 051-source-image-intake
implemented: false
---

# Story: 003-source-image-rejection

## User Story

**As a** responsable de la integridad del puente
**I want** que toda subida inválida, ajena o incoherente con lo declarado falle de forma cerrada y explícita
**So that** ningún photoshoot se ejecute sobre bytes que nadie verificó y ninguna imagen cruce la frontera entre productos o entre tenants

## Acceptance Criteria

- [ ] **Given** una imagen de origen que pertenece a otro `product_link`, **When** intento confirmarla desde este producto, **Then** recibo `403`, no se registra media y no se revela si la imagen existe
- [ ] **Given** un `ServiceClient` de otro tenant, **When** intenta el presign o la confirmación sobre este producto, **Then** recibe `403`/`404` y no se firma ni se registra nada
- [ ] **Given** un `staff_id` revocado o sin rol de staff, **When** solicita presign o confirmación, **Then** recibe `403` en ambos endpoints
- [ ] **Given** un objeto cuyo `content_type` real difiere del declarado en el presign, **When** confirmo, **Then** la imagen queda `rejected` con `rejection_reason` explícito y **no** en `ready`
- [ ] **Given** un objeto cuyo tamaño real supera el límite configurado, **When** confirmo, **Then** la imagen queda `rejected` con el tamaño medido en el motivo
- [ ] **Given** un objeto que no es una imagen decodificable, **When** confirmo, **Then** la imagen queda `rejected` y no se registra media
- [ ] **Given** una imagen en `rejected`, **When** intento confirmarla de nuevo, **Then** recibo `409` y sigue en `rejected`: el rechazo es terminal para esa reserva
- [ ] **Given** cualquier rechazo, **When** leo la respuesta, **Then** el motivo es lo bastante concreto para que BFashion se lo muestre al staff, sin filtrar rutas internas, claves de almacenamiento ni credenciales

## Technical Notes

- Este es el sitio donde se prueba de verdad FR-15 para esta unidad. Los casos cross-tenant y cross-product deben tener pruebas dedicadas, no quedar implícitos en las historias anteriores.
- Reutilizar `media_service._validate_file` para la validación de contenido, de modo que el criterio sea el mismo que en los flujos cookie-auth.
- El rechazo es terminal para la reserva: el camino de recuperación es pedir un presign nuevo, no reciclar una reserva rechazada. Así el estado no admite ambigüedad.
- No revelar existencia: una imagen ajena y una inexistente deben responder igual desde fuera.

## Dependencies

### Requires
- `001-source-image-presign`
- `002-source-image-confirm`

### Enables
- Ninguna (cierra la unidad)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Imagen sustituida en el almacenamiento entre el `PUT` y la confirmación | Se valida lo que hay en el momento de confirmar; si no coincide con lo declarado, `rejected` |
| Confirmación con `source_image_id` de un producto del mismo tenant pero distinto | `403`: la propiedad se lee del `product_link`, no del tenant |
| Archivo con extensión `.png` y bytes JPEG | Manda el contenido real; si contradice lo declarado, `rejected` con motivo |
| Petición sin cabeceras de servicio | `401`, antes de cualquier resolución de vínculo |

## Out of Scope

- Cuarentena o análisis antivirus
- Reintento automático tras un rechazo
- Purga programada de reservas `rejected`

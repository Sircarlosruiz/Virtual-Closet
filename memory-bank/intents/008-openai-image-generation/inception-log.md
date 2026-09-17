---
intent: 008-openai-image-generation
created: 2026-09-17T00:28:03Z
completed: 2026-09-17T01:39:14Z
status: complete
---

# Inception Log: 008-openai-image-generation

## Overview

**Intent**: Integrar OpenAI para generación de prendas sobre modelos, generación desde texto, edición, extracción y plantillas reutilizables.
**Type**: brown-field
**Created**: 2026-09-17T00:28:03Z

## Artifacts Created

| Artifact | Status | File |
|----------|--------|------|
| Requirements | Aprobados en Checkpoint 2: 13 FR y 5 NFR | requirements.md |
| System Context | Aprobado en Checkpoint 3 | system-context.md |
| Units | 4 unidades; aprobadas en Checkpoint 3 | units.md, units/*/unit-brief.md |
| Stories | 14 historias generadas; aprobadas en Checkpoint 3 | units/*/stories/*.md |
| Bolt Plan | 7 bolts generados; aprobado en Checkpoint 3 | memory-bank/bolts/043-049/bolt.md |

## Summary

| Metric | Count |
|--------|-------|
| Functional Requirements aprobados | 13 |
| Non-Functional Requirements aprobados | 5 |
| Units | 4 |
| Stories | 14 |
| Bolts Planned | 7 |

## Units Breakdown

| Unit | Stories | Bolts | Priority |
|---|---:|---:|---|
| 001-image-generation-service | 5 | 2 (043, 044) | Must |
| 002-template-composition-service | 3 | 2 (045, 046) | Must |
| 003-product-image-integration | 3 | 2 (047, 048) | Must |
| 004-openai-generation-ui | 3 | 1 (049) | Must |

## Decision Log

| Date | Decision | Rationale | Approved |
|------|----------|-----------|----------|
| 2026-09-17T00:28:03Z | Incluir prendas sobre modelos, generación desde texto y edición de imágenes | El usuario solicitó las tres capacidades | Sí, alcance general |
| 2026-09-17T00:28:03Z | Incluir plantillas con modelo, fondo, colores, percheros y códigos | Características expresadas por el usuario | Sí, alcance general |
| 2026-09-17T00:28:03Z | Incluir extracción de prendas y prompts/ajustes guardados | El usuario confirmó ambas capacidades | Sí, alcance general |
| 2026-09-17T00:28:03Z | Usar una única API key de la plataforma | Modalidad elegida explícitamente por el usuario | Sí |
| 2026-09-17T00:32:09Z | Ofrecer OpenAI como alternativa seleccionable al proveedor actual en prendas sobre modelos y usar OpenAI para las nuevas capacidades | El usuario eligió la opción 1; se conserva el proveedor actual | Sí |
| 2026-09-17T00:36:41Z | Mostrar los códigos de prendas como referencias o SKU visibles en la imagen | El usuario eligió la opción 1, por ejemplo `REF: CAM-001` | Sí |
| 2026-09-17T00:39:25Z | Reservar la creación de plantillas al staff y destinarlas a los productos del ecommerce | Aclaración explícita del usuario; distribución y contenido a almacenar pendientes de precisar | Sí, alcance general |
| 2026-09-17T00:43:26Z | Ofrecer plantillas comunes de la plataforma y plantillas privadas de cada mayorista, con creación exclusiva del staff | El usuario confirmó ambas modalidades tras aclarar el permiso de creación | Sí |
| 2026-09-17T00:49:47Z | Guardar en los productos del ecommerce tanto las imágenes finales como la configuración de la plantilla utilizada | El usuario eligió la opción 3 para permitir generar nuevas versiones | Sí |
| 2026-09-17T00:52:58Z | Integrar resultados y configuraciones en Virtual Closet y en el ecommerce externo BFashion (`~/dev/bfashion/ecommerce`) | El usuario confirmó ambos destinos e identificó el repositorio externo | Sí |
| 2026-09-17T00:55:35Z | Permitir al staff iniciar la generación desde ambas aplicaciones y centralizar su ejecución en Virtual Closet | El usuario eligió la opción 3 | Sí |
| 2026-09-17T01:07:23Z | Incorporar imágenes a la galería del producto mediante previsualización y selección manual del staff | El usuario eligió la opción 1 | Sí |
| 2026-09-17T01:09:33Z | Crear plantillas mediante campos configurables e imágenes de referencia opcionales | El usuario eligió la opción 3 | Sí |
| 2026-09-17T01:11:54Z | Reservar toda la generación de este intent al staff; los mayoristas solo acceden a resultados publicados | El usuario eligió la opción 2; las plantillas privadas no habilitan generación por el mayorista | Sí |
| 2026-09-17T01:17:24Z | Adoptar el enfoque híbrido: escena generada por OpenAI y composición posterior del SKU/elementos fijos en Virtual Closet | El usuario aprobó explícitamente el enfoque 1 | Sí |
| 2026-09-17T01:17:24Z | Presentar 13 FR, 5 NFR y límites de primera versión para Checkpoint 2 | Consolidación del alcance confirmado y propuestas de aceptación técnica | Pendiente; no implica aprobación de requisitos |

## Scope Changes

Sin cambios respecto al alcance inicial registrado. Detalles funcionales pendientes.

## Revisión del borrador

- **2026-09-17T01:23:26Z:** revisión de consistencia completada en dos pasadas. Se aclararon campos opcionales de plantilla frente a entradas obligatorias por modo, regeneración desde configuración histórica de plantillas archivadas, versionado al recomponer SKU, ubicación propuesta de administración de plantillas y tratamiento de mensajes duplicados durante ejecución.
- Resultado del revisor: borrador apto para presentar en Checkpoint 2. No sustituye la aprobación del usuario; 13 FR, 5 NFR y límites V1 siguen pendientes.
- **2026-09-17T01:23:26Z:** contexto, 4 unidades, 14 historias y 7 bolts generados. Verificación local: todos los stories tienen bolt asignado y todos los bolts tienen dependencias explícitas.
- **2026-09-17T01:39:14Z:** Checkpoint 3 aprobado por el usuario. Inception completado; pendiente confirmar inicio de Construction.

## Ready for Construction

- [x] All requirements documented
- [x] System context defined
- [x] Units decomposed
- [x] Stories created for all units
- [x] Bolts planned
- [x] Human review complete

## Next Steps

1. Iniciar Construction con `043-image-generation-service`.
2. Ejecutar después los bolts según `requires_bolts`.
3. Mantener la revisión técnica de BFashion y OpenAI durante Construction.

## Dependencies

Por validar durante la definición de contexto: flujos VTON y TryOff existentes, biblioteca de medios, catálogos y autenticación multi-tenant. Se requiere una cuenta de la plataforma con acceso a la API de imágenes de OpenAI.

Destino externo confirmado: BFashion (`~/dev/bfashion/ecommerce`), backend Django REST y frontend React/TypeScript/Vite. Inspección inicial: `backend/catalog/models.py` contiene `Product` y `ProductImage`; este último ya vincula imágenes con productos. Pendientes: contrato entre aplicaciones, identidad del staff, correspondencia de mayoristas/productos y almacenamiento de configuraciones de generación.

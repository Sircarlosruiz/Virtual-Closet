---
intent: 008-openai-image-generation
phase: inception
status: draft
created: 2026-09-17T01:23:26Z
updated: 2026-09-17T01:23:26Z
---

# Unit Decomposition: 008-openai-image-generation

## Units

### 001-image-generation-service
- **Type**: backend / domain-driven
- **Purpose**: Ejecutar modos OpenAI y VTON alternativo como trabajos asíncronos, con autorización de staff, historial, reintentos y consumo.
- **Primary Requirements**: FR-1, FR-2, FR-5, FR-6, FR-7, FR-8, FR-9, FR-13
- **Dependencies**: Auth existente, media/storage, RabbitMQ/Celery.
- **Interface**: API de trabajos y eventos internos para UI, plantillas e integración.
- **Default Bolt Type**: ddd-construction-bolt

### 002-template-composition-service
- **Type**: backend / domain-driven
- **Purpose**: Versionar plantillas comunes/privadas, construir prompts y componer SKU/overlays deterministas.
- **Primary Requirements**: FR-3, FR-4, FR-10
- **Dependencies**: 001 para resultados y 003 para producto externo.
- **Interface**: API de plantillas, snapshot de configuración efectiva y compositor.
- **Default Bolt Type**: ddd-construction-bolt

### 003-product-image-integration
- **Type**: backend / integration
- **Purpose**: Vincular productos, publicar selecciones manuales y sincronizar imágenes/configuración con BFashion.
- **Primary Requirements**: FR-11, FR-12
- **Dependencies**: 001 y 002; contrato de producto de BFashion.
- **Interface**: API server-to-server, adaptador BFashion y estados idempotentes de entrega.
- **Default Bolt Type**: simple-construction-bolt

### 004-openai-generation-ui
- **Type**: frontend / feature-based
- **Purpose**: Exponer generación, plantillas, revisión y publicación para staff en Virtual Closet; soportar entrada desde BFashion.
- **Primary Requirements**: Presentación de FR-1..FR-12; no posee reglas de autorización ni persistencia como fuente de verdad.
- **Dependencies**: 001, 002 y 003.
- **Interface**: APIs de backend y contrato de integración BFashion.
- **Default Bolt Type**: simple-construction-bolt

## Requirement-to-Unit Mapping

- **FR-1, FR-2, FR-5, FR-6, FR-7, FR-8, FR-9, FR-13** → `001-image-generation-service`
- **FR-3, FR-4, FR-10** → `002-template-composition-service`
- **FR-11, FR-12** → `003-product-image-integration`
- UI de FR-1..FR-12 → `004-openai-generation-ui` como consumidor/presentación, sin duplicar ownership de dominio.

## Dependency Graph

```text
001-image-generation-service ──► 002-template-composition-service
            │                         │
            └──────────────► 003-product-image-integration
                                      │
                         004-openai-generation-ui
```

## Independence Checks

- Cada unidad tiene un contrato explícito y stories acotadas.
- El servicio de generación puede probarse sin BFashion usando storage/queue stubs.
- Plantillas y composición preservan snapshots históricos sin depender de una plantilla viva.
- La integración BFashion puede fallar sin perder un resultado generado en Virtual Closet.
- La UI no contiene secretos ni decisiones de autorización.

---
intent: 008-openai-image-generation
phase: inception
status: complete
created: 2026-09-17T00:28:03.000Z
updated: 2026-09-17T01:39:14.000Z
---

# Requirements: Generación de imágenes con OpenAI

## Intent Overview

Integrar la API de OpenAI en Virtual Closet para generar y editar imágenes de prendas, utilizando una única API key de la plataforma. Ampliación de la plataforma existente (brown-field).

Alcance funcional y enfoque híbrido confirmados. Requisitos detallados en borrador para Checkpoint 2; su aprobación sigue pendiente. Los criterios de aceptación y límites de primera versión son propuestas para esa revisión, no decisiones previamente aprobadas.

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Generar imágenes de prendas sobre modelos mediante OpenAI | Validación visual según NFR-3 y selección del staff | Must |
| Reutilizar composiciones y ajustes mediante plantillas | Regenerar desde configuraciones históricas sin sobrescribirlas | Must |
| Crear, editar y extraer imágenes de prendas dentro de la plataforma | Completar los cuatro modos desde ambas aplicaciones | Must |
| Incorporar resultados a productos del ecommerce | Publicar la selección del staff con su configuración, sin duplicados | Must |

## Alcance confirmado

- Generación de prendas sobre modelos a partir de fotografías de referencia.
- Generación de imágenes desde descripciones de texto (prompts).
- Edición de imágenes existentes mediante instrucciones.
- Plantillas reutilizables con características como modelo, fondo, colores, percheros y códigos de prendas.
- Solo el staff puede crear las plantillas. En los productos del ecommerce se guardarán las imágenes finales y la configuración de la plantilla utilizada, para poder generar nuevas versiones.
- Existirán plantillas comunes de la plataforma y plantillas privadas de cada mayorista. La creación de ambas modalidades queda reservada al staff.
- Las imágenes y configuraciones se integrarán tanto en Virtual Closet como en el ecommerce externo BFashion, cuyo repositorio está en `~/dev/bfashion/ecommerce`.
- El staff podrá iniciar la generación desde Virtual Closet o desde la administración del ecommerce. La ejecución de la generación se centralizará en Virtual Closet.
- La incorporación a la galería del producto será manual: el staff previsualiza los resultados y selecciona las imágenes que desea añadir.
- El staff creará las plantillas mediante campos configurables (modelo, fondo, colores, percheros y ubicación del SKU), con imágenes de referencia opcionales para guiar la composición.
- Toda la generación cubierta por este intent será exclusiva del staff. Los mayoristas solo accederán a los resultados publicados; disponer de plantillas privadas no les concede permisos para crearlas ni utilizarlas directamente para generar.
- Los códigos de prendas son referencias o SKU visibles en la imagen (por ejemplo, `REF: CAM-001`).
- Extracción de prendas desde fotografías para reutilizarlas sin la persona.
- Prompts y ajustes guardados para mantener un estilo consistente.
- Una única API key de la plataforma; no claves aportadas por cada mayorista.
- OpenAI como alternativa seleccionable al proveedor actual para generar prendas sobre modelos; OpenAI se utilizará para las nuevas capacidades.
- Enfoque híbrido aprobado: OpenAI genera la escena siguiendo campos y referencias; Virtual Closet incorpora el SKU y los elementos de posición fija mediante composición posterior.

## Functional Requirements

Todos los requisitos funcionales tienen prioridad **Must**. Los criterios siguientes se presentan completos para aprobación.

### FR-1: Operación exclusiva del staff
- **Descripción:** Solo el staff autorizado administra plantillas, genera y publica imágenes de este intent.
- **Aceptación:** Ambas aplicaciones verifican permisos en servidor. Mayoristas sin permiso de staff no pueden invocar estas operaciones ni consultar borradores o configuraciones privadas; acceden a resultados publicados. Una plantilla privada solo se aplica al mayorista asignado. Ser administrador de un mayorista no concede automáticamente permisos de staff de plataforma.

### FR-2: Credencial y selección del proveedor
- **Descripción:** Virtual Closet usa una API key de plataforma y permite elegir OpenAI o el proveedor VTON existente para prendas sobre modelos.
- **Aceptación:** La clave reside en servidor y no se entrega al navegador ni al ecommerce. Cada trabajo conserva el proveedor elegido. Texto, edición y extracción de este intent usan OpenAI. Sin credencial válida se informa indisponibilidad; no se cambia de proveedor silenciosamente. Una combinación de opciones no soportada se rechaza antes de generar.

### FR-3: Plantillas comunes y privadas
- **Descripción:** El staff crea, edita y archiva plantillas comunes o asignadas a un mayorista.
- **Aceptación:** Nombre y alcance son obligatorios; modelo, fondo, colores, percheros, prompt, ajustes, ubicación/estilo del SKU y referencias visuales son opcionales en la plantilla. Se validan las entradas requeridas por cada modo al generar. La interfaz distingue colores de la escena de cambios solicitados a la prenda. Editar o archivar no altera el historial; archivar impide seleccionar la plantilla, pero permite regenerar desde la copia histórica de un resultado.

### FR-4: Composición híbrida y SKU exacto
- **Descripción:** OpenAI produce la escena y Virtual Closet añade el SKU y los elementos de posición fija.
- **Aceptación:** El SKU se toma del producto o se introduce explícitamente y se guarda con el trabajo. El compositor respeta texto, posición, fuente, tamaño y color configurados; valida que el texto quepa completo. Si se incluye SKU, sus ajustes se completan antes de componer. Se conserva la imagen base sin superposición. Cambiar solo el SKU o su estilo crea una nueva versión sin llamar de nuevo a OpenAI ni reemplazar la publicada; publicarla requiere selección del staff. Modelo, fondo y percheros son instrucciones/referencias generativas, no posiciones exactas garantizadas.

### FR-5: Prendas sobre modelos
- **Descripción:** Generar una composición usando una fotografía de la prenda y una del modelo.
- **Aceptación:** El staff selecciona ambas imágenes, tipo de prenda, proveedor y plantilla opcional; puede reutilizar una referencia de modelo de la plantilla sin cargarla otra vez. El prompt solicita conservar identidad del modelo y características de la prenda, salvo cambios explícitos. Se muestran referencias y resultado para comparación; la aceptación visual corresponde al staff según NFR-3. Este modo requiere ambas fotografías; crear una escena con un modelo descrito por texto corresponde a FR-6.

### FR-6: Generación desde texto
- **Descripción:** Crear imágenes desde un prompt, con plantilla opcional.
- **Aceptación:** Se exige un prompt no vacío, se aplican los campos y referencias de la plantilla elegida y se produce un resultado previsualizable. No se exige una fotografía de prenda en este modo.

### FR-7: Edición de imágenes
- **Descripción:** Modificar una imagen mediante instrucciones del staff.
- **Aceptación:** Se selecciona una imagen y un cambio textual. La edición crea un resultado nuevo vinculado al original, sin sobrescribirlo. Para resultados híbridos se edita la imagen base y después se reaplica el SKU; el staff puede repetir el proceso desde un resultado previo.

### FR-8: Extracción de prendas
- **Descripción:** Obtener una imagen de una prenda aislada a partir de una fotografía con una persona.
- **Aceptación:** El staff identifica la prenda a extraer. Se genera sobre fondo neutro, se previsualiza y se puede reutilizar como entrada de prendas sobre modelos. Se conserva la relación con la foto original. Propuesta V1: extraer una prenda por trabajo.

### FR-9: Trabajos asíncronos e historial
- **Descripción:** Ejecutar en Virtual Closet todos los trabajos iniciados desde cualquiera de las aplicaciones.
- **Aceptación:** Cada solicitud devuelve un identificador y expone estados en cola, procesando, completado o fallido. El historial conserva actor, mayorista, modo, proveedor, entradas, tiempos y errores. Cerrar la pantalla no cancela el trabajo. Un resultado completado significa disponible para revisión, no publicado. Propuesta V1: un resultado por trabajo.

### FR-10: Persistencia y regeneración
- **Descripción:** Guardar imágenes y una copia de la configuración efectiva para generar nuevas versiones.
- **Aceptación:** Se conservan imagen base, imagen final, referencias, prompt, proveedor/modelo, ajustes, versión de plantilla y configuración del compositor. Las imágenes aceptadas y su configuración se vinculan al producto en ambos sistemas. Regenerar crea un trabajo nuevo, mantiene el historial y no promete una imagen idéntica. Si falta una referencia o el modelo ya no está disponible, se pide corregir la configuración explícitamente.

### FR-11: Integración Virtual Closet–BFashion
- **Descripción:** El staff inicia y consulta los cuatro modos desde Virtual Closet y desde la administración del producto en BFashion.
- **Aceptación:** La comunicación es servidor a servidor, autenticada y asociada al actor autorizado. Se valida una correspondencia explícita entre mayorista, producto BFashion y entidad vinculada en Virtual Closet; no se deduce solo por SKU. BFashion delega la generación en Virtual Closet y recibe imágenes/configuración. Ante un vínculo ausente, inválido o ajeno al mayorista, se informa el error sin publicar en otro producto.

### FR-12: Selección y publicación manual
- **Descripción:** El staff decide qué resultados incorporar a la galería del producto.
- **Aceptación:** Se pueden previsualizar, seleccionar o descartar resultados. Solo los seleccionados se añaden a la galería; no se reemplazan imágenes existentes automáticamente. Cada destino muestra pendiente, sincronizado o fallido. Reintentar la publicación no duplica imágenes ni ejecuta otra generación. La copia en el ecommerce sigue disponible aunque caduque una URL temporal de transferencia.

### FR-13: Registro de consumo
- **Descripción:** Registrar el uso de OpenAI por trabajo y mayorista bajo la cuenta de la plataforma.
- **Aceptación:** Se guarda modelo, número de llamadas, uso informado por el proveedor y resultado. Si el proveedor no informa consumo, se registra como desconocido, no como cero. Cualquier costo calculado se identifica como estimación. Propuesta V1: límites configurables de concurrencia y tamaño de solicitud; sin facturación automática al mayorista.

## Non-Functional Requirements

Todos los requisitos no funcionales tienen prioridad **Must**. Los valores numéricos son propuestas para aprobación.

### NFR-1: Respuesta y límites de ejecución
- **Métrica y criterio:** En una prueba con 10 sesiones de staff, envío de trabajo y consulta de estado tendrán p95 ≤ 1 s, excluyendo carga de archivos y tiempo de OpenAI. Propuesta inicial: 2 llamadas OpenAI simultáneas por despliegue; el excedente queda en cola. Timeout por llamada de 300 s, configurable; al vencer, el estado de fallo se refleja en ≤ 30 s. El tiempo de cola se muestra por separado.

### NFR-2: Recuperación y duplicados
- **Métrica y criterio:** Repetir una solicitud con la misma clave de idempotencia y contenido produce un único trabajo; cambiar el contenido con esa clave genera conflicto. Duplicar mensajes durante ejecución no inicia llamadas concurrentes para el mismo intento ni repite un resultado persistido. Errores no transitorios no se reintentan automáticamente; los 429 tienen como máximo 2 reintentos respetando Retry-After. Un timeout con resultado desconocido requiere reintento explícito. Un fallo de almacenamiento o publicación se recupera desde el resultado persistido cuando exista, sin llamar otra vez a OpenAI.

### NFR-3: Calidad visual y composición
- **Métrica y criterio:** La validación previa a entrega incluye al menos 6 prendas sobre modelos —2 superiores, 2 inferiores y 2 vestidos— y 2 casos por cada modo adicional. El staff registra aceptación/rechazo según conservación de color, silueta, estampado y detalles relevantes, identidad del modelo cuando corresponda, y cambios solicitados. Cada modo debe aportar al menos un resultado aceptado. Los casos del compositor deben conservar el SKU exacto y completo, con posición verificable dentro de la imagen. Se mide la tasa de aceptación; no se promete fidelidad automática de todos los resultados.

### NFR-4: Privacidad e integridad de acceso
- **Métrica y criterio:** Las pruebas verifican que un mayorista no accede a borradores, configuración o referencias privadas de otro. La credencial OpenAI no aparece en respuestas ni registros. La integración comprueba identidad de servicio, autorización de staff y correspondencia de producto/mayorista; falsificar esos identificadores no habilita generación ni publicación.

### NFR-5: Durabilidad e historial
- **Métrica y criterio:** Reiniciar servicios mantiene trabajos, selección, configuración y estado de sincronización. Una imagen no se marca completada hasta persistir su archivo y configuración; un destino no se marca sincronizado hasta confirmar imagen y configuración. Editar o archivar la plantilla no cambia la copia histórica. Se conservan referencias duraderas de almacenamiento, no solo URLs temporales.

## Constraints

### Technical Constraints

- Integración con la API de imágenes de OpenAI. Se propone Image API (generación y edición); el identificador concreto de modelo será configurable y se validará con la cuenta de plataforma y los casos de NFR-3 antes de habilitarlo.
- La credencial pertenece a la plataforma. Su configuración se realizará del lado del servidor, sin incluir su valor en los artefactos de planificación.
- El staff podrá elegir OpenAI o el proveedor actual para prendas sobre modelos. Se propone que la extracción OpenAI sea un modo de este nuevo flujo, sin sustituir el flujo TryOff existente.
- El ecommerce externo utiliza Django REST y React/TypeScript/Vite. En `backend/catalog/models.py` existen `Product` y `ProductImage`; este último vincula imágenes al producto mediante URL, clave de almacenamiento, metadatos y orden. El contrato de integración y la persistencia de configuraciones de generación quedan por diseñar.

### Business Constraints

- El consumo de OpenAI se centraliza en la cuenta de la plataforma.
- No se ha acordado un presupuesto monetario ni facturación al mayorista. Este borrador propone registro de consumo y límites técnicos, sin introducir cuotas comerciales.

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| La composición de SKU mediante campos cubre la primera versión | Se necesitaría un editor visual más amplio | Validar esta propuesta en Checkpoint 2 |
| El staff puede vincular explícitamente productos y mayoristas entre aplicaciones | Publicación ambigua o destino incorrecto | Definir el contrato y la autoridad de cada identificador durante contexto y unidades |

## Diseño propuesto y validación técnica

- **Plantillas y composición:** Virtual Closet conserva plantillas versionadas y configura el compositor determinista del SKU. En V1, el SKU es el único elemento fijo exigido; otros overlays necesitan requisitos adicionales.
- **Generación:** API y workers de Virtual Closet coordinan validación, trabajos, proveedores e historial. Se reutilizan Celery/RabbitMQ y almacenamiento del proyecto; generación, composición y publicación tienen recuperación diferenciada.
- **Integración:** un adaptador servidor a servidor conecta BFashion con Virtual Closet. BFashion conserva su producto y galería, además de la copia de configuración de cada resultado aceptado. Los identificadores de trabajo y resultado permiten deduplicar entregas.
- **Interfaces:** cada aplicación expone el flujo de generación del staff; ambas consumen el mismo servicio. Propuesta V1: las plantillas se crean y administran en Virtual Closet, y pueden seleccionarse para generar desde ambas aplicaciones.
- **Verificación:** pruebas de permisos, aislamiento por mayorista, composición exacta, snapshots, contratos entre servicios, reintentos e idempotencia; pruebas de los flujos de staff desde ambas interfaces y evaluación visual con OpenAI según NFR-3.
- **Evidencia:** `backend/services/providers/vton_provider.py` expone `generate(garment_url, model_url, cloth_type)`. La selección por trabajo y los modos adicionales requieren diseño específico; no se asume que el contrato VTON actual cubra texto, edición y extracción.
- **Evidencia externa:** BFashion expone modelos `Product` y `ProductImage` en `backend/catalog/models.py`; este último guarda URL, clave de almacenamiento, tipo, tamaño, texto alternativo y orden. La copia de configuración y el vínculo de integración son capacidades nuevas a diseñar.
- **Referencia oficial consultada:** https://developers.openai.com/api/docs/guides/image-generation — generación desde texto y edición con imágenes de referencia. La documentación no sustituye la evaluación de fidelidad de prendas del caso de uso.

## Out of Scope

- Configuración de claves OpenAI individuales por mayorista en este intent, según la modalidad elegida.
- Propuestas V1 para aprobación: sin editor libre tipo lienzo, códigos QR/barras, generación masiva de productos, expansión automática a múltiples poses, chatbot conversacional ni sincronización de precios/inventario.
- La restricción de staff aplica a este intent; no migra los permisos de los flujos VTON anteriores.

## Open Questions

| Question | Owner | Resolution |
|----------|-------|------------|
| ¿OpenAI coexistirá como alternativa seleccionable, será el proveedor predeterminado o sustituirá los flujos actuales? | Usuario | Resuelto: alternativa seleccionable para prendas sobre modelos; OpenAI para las nuevas capacidades |
| ¿Cómo crea el staff una plantilla? | Usuario | Resuelto: campos configurables e imágenes de referencia opcionales |
| ¿Qué elementos requieren posiciones exactas? | Usuario | Enfoque híbrido aprobado; propuesta V1: SKU determinista y escena generativa |
| ¿Los códigos son texto visible, identificadores internos, códigos de barras o QR? | Usuario | Resuelto: referencia o SKU visible en la imagen |
| ¿Quién crea las plantillas y qué modalidades existen? | Usuario | Resuelto: creación exclusiva del staff; plantillas comunes de la plataforma y plantillas privadas de cada mayorista |
| ¿Quién puede aplicar las plantillas y generar imágenes? | Usuario | Resuelto: solo el staff; los mayoristas únicamente acceden a resultados publicados |
| ¿Quién puede editar y eliminar las plantillas? | Usuario | Propuesta FR-3: staff autorizado edita y archiva, preservando historial |
| ¿Qué se almacena dentro de los productos del ecommerce? | Usuario | Resuelto: imágenes finales y configuración de la plantilla utilizada para generar nuevas versiones |
| ¿Qué ecommerce recibe las imágenes y configuraciones de plantilla? | Usuario | Resuelto: Virtual Closet y BFashion, repositorio `~/dev/bfashion/ecommerce` |
| ¿Desde qué aplicación inicia el staff la generación y asociación de imágenes a productos? | Usuario | Resuelto: ambas aplicaciones, con generación centralizada en Virtual Closet |
| ¿Las imágenes generadas se publican automáticamente en el producto o requieren selección del staff? | Usuario | Resuelto: previsualización y selección manual del staff antes de añadir imágenes a la galería del producto |
| ¿Qué fidelidad visual y exactitud se exige? | Usuario | Propuesta NFR-3 para revisión; SKU determinista y evaluación humana de la escena |
| ¿Qué límites operativos se aplican? | Usuario | Propuestas FR-9, FR-13 y NFR-1; resolución/calidad admitidas según modelo validado, almacenadas por trabajo |
| ¿Qué se incluye en la primera versión? | Usuario | Cuatro modos, plantillas y publicación en ambos sistemas; propuestas de exclusión indicadas arriba |
| ¿Cómo se materializan identidades de staff y vínculos producto/mayorista entre sistemas? | Diseño de contexto/unidades | Debe especificarse antes de completar Inception; no asumir que roles ni IDs coinciden |

## Estado de revisión

- Checkpoint 1: decisiones principales recogidas.
- Enfoque híbrido: aprobado por el usuario.
- Checkpoint 2: pendiente de aprobación de los 13 FR, 5 NFR y límites propuestos.
- Contexto, unidades, historias y bolts: se elaborarán después de Checkpoint 2 y se revisarán juntos en Checkpoint 3.

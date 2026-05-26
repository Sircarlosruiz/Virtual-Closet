# Arquitectura Técnica — Virtual Closet MVP
## NikaCommerce · Versión 1.0

**Basado en:** PRFAQ v1.0  
**Alcance:** MVP — prendas superiores, modelos predefinidos, catálogo con link compartible  
**Principio rector:** Open-source, self-hosted en Kubernetes. GPU local para desarrollo, Replicate API para producción. Costo mínimo desde el día 1.

---

## 1. Flujo del sistema (end-to-end)

```
MAYORISTA                     BACKEND                        REVENDEDOR
─────────                     ───────                        ──────────
Sube foto de prenda           Almacena imagen en MinIO
    │                              │
    │                         Publica mensaje en RabbitMQ
    │                              │
    │                     ┌────────▼────────┐
    │                     │ Celery Worker   │
    │                     │ DEV:  GPU local │
    │                     │ PROD: Replicate │
    │                     └────────┬────────┘
    │                              │
    │                         Guarda resultado en MinIO
    │                              │
    │◄──── WebSocket: "lista" ─────┤
    │                              │
Revisa y publica catálogo     Genera link único + QR
    │                              │
Comparte link por WhatsApp ─────────────────────────────► Abre catálogo en browser
                                                                (sin login)
```

---

## 2. Stack tecnológico

| Capa | Tecnología | Licencia | Costo |
| --- | --- | --- | --- |
| Frontend | **Next.js 14** | MIT | $0 |
| Backend API | **FastAPI (Python)** | MIT | $0 |
| Base de datos | **PostgreSQL 16** | PostgreSQL License | $0 |
| Cola de mensajes | **RabbitMQ** | MPL 2.0 | $0 |
| Workers | **Celery (Python)** | BSD | $0 |
| Storage de imágenes | **MinIO** | AGPL / SSPL | $0 self-hosted |
| Reverse proxy | **Nginx Ingress Controller** | Apache 2.0 | $0 |
| Orquestación | **Kubernetes (k3s)** | Apache 2.0 | $0 |
| Contenedores | **Docker** | Apache 2.0 | $0 |
| TLS | **cert-manager + Let's Encrypt** | Apache 2.0 | $0 |
| IA — VTON (desarrollo) | **IDM-VTON local** (GPU propia) | Apache 2.0 | $0 |
| IA — VTON (producción) | **Replicate API** (IDM-VTON) | Pay per use | ~$0.05/imagen |
| Auth | **JWT + HttpOnly cookies** | — | $0 |
| Infra cloud (producción) | **Hetzner Cloud** | — | ~€31/mes |

---

## 3. Entornos: desarrollo vs. producción

```
┌─────────────────────────────────────────────────────┐
│              DESARROLLO (local)                     │
│                                                     │
│  Docker Compose:                                    │
│  - nextjs (hot reload)                              │
│  - fastapi (uvicorn --reload)                       │
│  - celery worker                                    │
│  - postgresql                                       │
│  - rabbitmq                                         │
│  - minio                                            │
│  - vton-server ◄── IDM-VTON en NVIDIA Titan RTX    │
│                    (nvidia-docker, 24GB VRAM)       │
│                    API REST local en :8001          │
│                                                     │
│  Variable: VTON_PROVIDER=local                      │
│  URL:      VTON_LOCAL_URL=http://vton-server:8001   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              PRODUCCIÓN (Kubernetes / Hetzner)      │
│                                                     │
│  - nextjs (2 pods)                                  │
│  - fastapi (2 pods)                                 │
│  - celery worker (2 pods)                           │
│  - postgresql (StatefulSet)                         │
│  - rabbitmq (StatefulSet)                           │
│  - minio (StatefulSet)                              │
│                                                     │
│  Variable: VTON_PROVIDER=replicate                  │
│  URL:      Replicate API (IDM-VTON)                 │
└─────────────────────────────────────────────────────┘
```

---

## 4. Capa de abstracción para proveedores de IA

El worker usa una interfaz única — cambiar de local a Replicate es solo una variable de entorno:

```python
# services/vton_provider.py

class VTONProvider(Protocol):
    async def generate(self, garment_img: bytes, model_img: bytes) -> bytes: ...

class LocalGPUProvider:
    """Usa IDM-VTON corriendo localmente en la Titan RTX."""
    async def generate(self, garment_img, model_img):
        response = await httpx.post(
            settings.VTON_LOCAL_URL + "/generate",
            files={"garment": garment_img, "model": model_img}
        )
        return response.content

class ReplicateProvider:
    """Usa Replicate API en producción. Pago por uso."""
    async def generate(self, garment_img, model_img):
        output = await replicate.async_run(
            "cuuupid/idm-vton:...",
            input={"human_img": encode_b64(model_img), "garment_img": encode_b64(garment_img)}
        )
        return await download(output[0])

def get_provider() -> VTONProvider:
    if settings.VTON_PROVIDER == "local":
        return LocalGPUProvider()
    return ReplicateProvider()
```

---

## 5. IDM-VTON local en Titan RTX

```yaml
# docker-compose.dev.yml (servicio vton)

vton-server:
  image: nikacommerce/vton-server:latest   # imagen propia basada en IDM-VTON
  build:
    context: ./services/vton
    dockerfile: Dockerfile.gpu
  runtime: nvidia
  environment:
    - NVIDIA_VISIBLE_DEVICES=all
    - MODEL_PATH=/models/idm-vton
  volumes:
    - ./models:/models                    # pesos descargados de HuggingFace
  ports:
    - "8001:8001"
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

**Requisitos del Titan RTX para IDM-VTON:**
- VRAM necesaria: ~12–16GB (fp16) → Titan RTX tiene 24GB ✓
- CUDA: 11.x o superior
- Tiempo de inferencia local estimado: 15–30s por imagen (sin cola)
- Los pesos de IDM-VTON se descargan de HuggingFace Hub (~6GB) una sola vez

---

## 6. RabbitMQ — Diseño de colas

```
Exchange: vton.direct
  │
  ├── Queue: vton.generation.normal     (plan Base — mayoría de jobs)
  │     TTL: 30 min, max_length: 500
  │
  ├── Queue: vton.generation.priority   (plan Pro)
  │     TTL: 10 min, max_length: 100
  │
  └── Queue: vton.generation.dead       (dead-letter — 3 reintentos fallidos)
        Alerta automática al equipo

Mensaje de job:
{
  "prenda_id": "uuid",
  "modelo_ia_id": "uuid",
  "imagen_original_key": "{mayorista_id}/{prenda_id}/original.{ext}",
  "mayorista_plan": "base|pro",
  "retry_count": 0,
  "enqueued_at": "ISO8601"
}
```

---

## 7. Modelo de datos (MVP)

**Fuente canónica** para implementación. Alineado con `epics.md` y el esquema PostgreSQL en `backend/models/`. Las prendas pertenecen al mayorista (`mayorista_id`); la relación con catálogos es M:N vía `catalogo_prenda` (no `catalogo_id` en `prenda`).

```sql
mayorista
  id UUID PK, email, password_hash, nombre_negocio
  plan ENUM('base','pro') DEFAULT 'base'
  trial_activo BOOLEAN DEFAULT true
  trial_expira_en TIMESTAMPTZ NOT NULL
  whatsapp VARCHAR(20) NULL
  created_at TIMESTAMPTZ

catalogo                          -- épica 4 (pendiente de migración)
  id UUID PK, mayorista_id FK, nombre
  slug VARCHAR(50) UNIQUE (por mayorista)
  estado ENUM('borrador','publicado') DEFAULT 'borrador'
  created_at, updated_at

catalogo_prenda                   -- M:N catálogo ↔ prenda
  catalogo_id FK, prenda_id FK, orden INTEGER
  PK (catalogo_id, prenda_id)

prenda                            -- implementado
  id UUID PK, mayorista_id FK, nombre VARCHAR(80)
  imagen_original_key TEXT        -- clave MinIO: {mayorista_id}/{prenda_id}/original.{ext}
  imagen_original_url TEXT        -- presigned URL o URL derivada (API/frontend)
  estado ENUM('pendiente','procesando','lista','error')
  created_at, updated_at

generacion                        -- implementado
  id UUID PK, mayorista_id FK, prenda_id FK, modelo_ia_id FK
  estado ENUM('pendiente','procesando','lista','error')
  imagen_generada_key TEXT        -- MinIO bucket generated
  thumbnail_key TEXT              -- MinIO bucket thumbnails
  costo_inferencia_usd NUMERIC(10,4)
  error_message TEXT NULL
  created_at, updated_at

modelo_ia                         -- implementado
  id UUID PK, mayorista_id FK NULL  -- modelos custom por mayorista (Pro)
  nombre, descripcion
  thumbnail_key TEXT
  plan_minimo ENUM('base','pro')
  created_at

catalogo_view_event               -- épica 5 (pendiente de migración)
  id UUID PK, catalogo_id FK
  ip_hash TEXT, user_agent TEXT, created_at
```

---

## 8. MinIO — Estructura de buckets

```
bucket originals (privado)
  └── {mayorista_id}/{prenda_id}/original.{ext}

bucket generated (presigned URL 24h)
  └── {mayorista_id}/{generacion_id}.jpg

bucket thumbnails (presigned URL 24h)
  └── {mayorista_id}/{generacion_id}.jpg   -- 400px

bucket model-thumbnails (público)
  └── {modelo_ia_id}/preview.jpg
```

---

## 9. Arquitectura de componentes (producción)

```
                        ┌──────────────────────────────────┐
                        │   Kubernetes Cluster (k3s)       │
                        │   Hetzner Cloud                  │
                        │                                  │
  ┌──────────┐  HTTPS   │  ┌────────────────────────────┐  │
  │  Browser │◄────────►│  │  Nginx Ingress + TLS       │  │
  └──────────┘          │  └──────┬─────────────────────┘  │
                        │         │                         │
                        │  ┌──────▼──────┐  ┌───────────┐  │
                        │  │  Next.js    │  │  FastAPI  │  │
                        │  │  (2 pods)   │  │  (2 pods) │  │
                        │  └─────────────┘  └─────┬─────┘  │
                        │                         │         │
                        │            ┌────────────▼──────┐  │
                        │            │    RabbitMQ       │  │
                        │            │  (StatefulSet)    │  │
                        │            └────────┬──────────┘  │
                        │                     │              │
                        │            ┌────────▼──────────┐  │
                        │            │  Celery Workers   │  │
                        │            │  (2 pods)         │  │
                        │            │  → Replicate API  │  │
                        │            └───────────────────┘  │
                        │                                  │
                        │  ┌───────────┐  ┌─────────────┐  │
                        │  │PostgreSQL │  │    MinIO    │  │
                        │  │(StatefulSet│  │(StatefulSet)│  │
                        │  └───────────┘  └─────────────┘  │
                        └──────────────────────────────────┘
                                    │ Replicate API
                                    ▼
                            ┌───────────────┐
                            │  IDM-VTON     │
                            │  GPU Cloud    │
                            └───────────────┘
```

---

## 10. Estimado de costos operativos (producción)

### Infraestructura Hetzner

| Recurso | Instancia | Costo/mes |
| --- | --- | --- |
| Nodo 1 (control plane + apps) | CX21 (2vCPU, 4GB) | €5.83 |
| Nodo 2 (workers + stateful) | CX31 (2vCPU, 8GB) | €9.17 |
| Load Balancer | LB11 | €5.83 |
| Volúmenes (200GB) | Block Storage | €9.60 |
| **Subtotal infra** | | **~€31/mes (~$34)** |

### Costo variable IA (Replicate)

| Escenario | Clientes | Imágenes/mes | Costo |
| --- | --- | --- | --- |
| Arranque | 10 | 400 | $20 |
| MVP estable | 50 | 2,000 | $100 |
| Crecimiento | 150 | 6,000 | $300 |

### Margen bruto

| Métrica | 10 clientes | 50 clientes | 150 clientes |
| --- | --- | --- | --- |
| Ingreso MRR | $390 | $1,950 | $5,850 |
| Costo total | ~$54 | ~$134 | ~$334 |
| **Margen bruto** | **~86%** | **~93%** | **~94%** |

---

## 11. Riesgos técnicos

| Riesgo | Prob. | Impacto | Mitigación |
| --- | --- | --- | --- |
| Replicate API caída en producción | Media | Alto | Dead-letter queue + retry con backoff; estado visible al mayorista |
| Divergencia dev/prod (GPU local vs. Replicate) | Media | Medio | Tests de integración contra Replicate en CI; nunca solo contra GPU local |
| MinIO con datos persistentes en k8s | Media | Alto | Backups diarios a Hetzner Object Storage ($0.023/GB) |
| Titan RTX sin disponibilidad para el dev | Baja | Bajo | Replicate usable en dev con flag `VTON_PROVIDER=replicate` |
| Costo IA supera estimado | Media | Medio | Cuota por plan (40 prendas/mes Base); alerta si se acerca al límite |

---

## 12. Secuencia de implementación

```
Sprint 1 — Fundación (2 semanas)
  ├── Docker Compose dev: todos los servicios + vton-server GPU local
  ├── Descargar pesos IDM-VTON y validar inferencia en Titan RTX
  ├── Auth: registro y login del mayorista (JWT)
  └── Upload: subida de foto de prenda a MinIO

Sprint 2 — Pipeline IA (2 semanas)
  ├── Celery worker + RabbitMQ: job de generación end-to-end
  ├── Abstracción VTONProvider: local (dev) / Replicate (prod)
  ├── WebSocket: notificación de job completado al dashboard
  └── Galería de resultados por prenda

Sprint 3 — Catálogo y sharing (1 semana)
  ├── Catálogo: agrupar prendas, publicar/despublicar
  ├── Slug único + página pública SSR (Next.js)
  ├── Código QR generado automáticamente
  └── OpenGraph meta para preview en WhatsApp

Sprint 4 — Infra producción y lanzamiento (1 semana)
  ├── k3s en Hetzner + Nginx Ingress + cert-manager
  ├── Deploy de todos los servicios en k8s
  ├── Free trial: 30 días Plan Base sin tarjeta + integración Stripe
  └── Prometheus + Grafana: monitoreo de costo IA por cliente
```

**Tiempo estimado a MVP funcional: 6–7 semanas con 1 desarrollador full-stack.**

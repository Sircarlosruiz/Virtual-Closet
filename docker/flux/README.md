# TryOff — servidor de inferencia FLUX (extracción de prendas)

Contenedor GPU que expone `POST /tryoff` y `GET /health`. Código en `main.py`; imagen definida en `Dockerfile`.

## Dos descargas en Hugging Face (obligatorio)

El producto TryOff que usamos es el **LoRA** [fal/virtual-tryoff-lora](https://huggingface.co/fal/virtual-tryoff-lora) (Apache-2.0, ~135 MB). Ese repo **solo** contiene pesos de adapter (`.safetensors`), no un pipeline completo.

Para inferencia con diffusers hace falta **además** la base que entrenó fal:

| Paso | Repo | Tamaño aprox. | Acceso HF |
|------|------|---------------|-----------|
| 1 — Base | [black-forest-labs/FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) | ~18 GB | **Gated** (licencia BFL) |
| 2 — LoRA TryOff | [fal/virtual-tryoff-lora](https://huggingface.co/fal/virtual-tryoff-lora) | ~135 MB | Público |

El flujo es el mismo que documenta fal en la card del LoRA: cargar `Flux2KleinPipeline` desde la base y luego `load_lora_weights("fal/virtual-tryoff-lora", ...)`.

```text
fal/virtual-tryoff-lora          black-forest-labs/FLUX.2-klein-base-9B
        (~135 MB LoRA)                    (~18 GB base)
              \                              /
               \                            /
                ---->  Pipeline TryOff  <----
```

**No es posible** levantar el servicio usando únicamente `fal/virtual-tryoff-lora`: sin la base no hay transformer ni VAE.

## Configuración previa (una vez por cuenta HF)

1. Iniciar sesión en [Hugging Face](https://huggingface.co).
2. Abrir [FLUX.2-klein-base-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B) y pulsar **Agree and access repository** (misma cuenta que el token).
3. Crear un token en [Settings → Access Tokens](https://huggingface.co/settings/tokens).

   **Recomendado:** token clásico tipo **Read** (acceso a repos gated sin opciones extra).

   Si usas token **fine-grained** (granular), activa obligatoriamente:
   - Permiso **Read** (o al menos acceso de lectura a repos)
   - **Access public gated repositories** / *Acceso a repositorios gated públicos*

   Sin esa casilla verás: `403 Forbidden: Please enable access to public gated repositories in your fine-grained token settings`.

4. En la raíz del monorepo, en `backend/.env`:

   ```env
   HF_TOKEN=hf_xxxxxxxx
   ```

   El servicio `tryoff-model` en `docker-compose.yml` carga `backend/.env` vía `env_file`.

5. (Opcional) Base distinta o copia local ya descargada:

   ```env
   TRYOFF_BASE_MODEL=black-forest-labs/FLUX.2-klein-base-9B
   ```

## Arranque local

Requisitos: NVIDIA GPU (~24 GB VRAM dedicados recomendados), Docker con soporte GPU, licencia BFL aceptada.

```bash
# Primera vez o tras cambiar Dockerfile/requirements
docker compose --profile gpu build tryoff-model

# Arranque (primera descarga de la base puede tardar mucho; caché en volumen tryoff_cache)
make docker-flux
# equivalente: docker compose --profile gpu up tryoff-model
```

Puerto host: **8003** → `http://localhost:8003/health`

```bash
make flux-test          # POST /tryoff de prueba
make flux-restart       # rebuild + health en :8003
```

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `HF_TOKEN` | — | Token HF para la base gated (no obligatorio para el LoRA público) |
| `TRYOFF_BASE_MODEL` | `black-forest-labs/FLUX.2-klein-base-9B` | Repo o ruta local de la base |
| `HF_HOME` | `/app/model_cache` | Caché Hugging Face (volumen `tryoff_cache`) |
| `TRYOFF_STEPS` | `28` | Pasos de difusión |
| `TRYOFF_GUIDANCE` | `5.0` | Guidance scale |
| `TRYOFF_HEIGHT` / `TRYOFF_WIDTH` | `1024` / `768` | Resolución de salida |
| `TRYOFF_LOW_VRAM` | `false` | `true` → CPU offload + VAE slicing (más lento, menos VRAM/RAM) |
| `TRYOFF_OFFLOAD` | `sequential` si low VRAM | `sequential` (menos RAM) o `model` (más rápido, más RAM) |

## Errores frecuentes

### `503` — GPU out of memory (OOM)

El modelo carga bien pero falla en el primer paso de difusión (`0%|…| 0/N`). Causas habituales:

- **FASHN o CatVTON** en la misma GPU: para TryOff, para el otro servicio (`docker compose stop fashn catvton`) o usa otra GPU.
- **VRAM &lt; 24 GB** con todo el pipeline en CUDA: en `docker-compose.yml` (servicio `tryoff-model`) o en el entorno del contenedor:

  ```env
  TRYOFF_LOW_VRAM=true
  TRYOFF_HEIGHT=512
  TRYOFF_WIDTH=512
  TRYOFF_STEPS=12
  ```

  Reinicia: `make flux-restart`.

- Tras un OOM, el worker Celery reintenta; espera a que termine la inferencia en curso o reinicia `tryoff-model` para liberar VRAM.

### El contenedor se reinicia solo (`exited with code 137`)

**137 = SIGKILL** — casi siempre el **OOM killer de Linux** (se acabó la **RAM del host**, no solo la VRAM de la GPU). Con `TRYOFF_LOW_VRAM=true` el modelo sigue usando mucha RAM del sistema al cargar la base (~18 GB) y en inferencia.

Qué hacer:

1. **No ejecutar FASHN/CatVTON a la vez** en la misma máquina (`docker compose stop fashn catvton`).
2. **WSL2:** en `%UserProfile%\.wslconfig` asigna más memoria, por ejemplo `memory=32GB`, luego `wsl --shutdown`.
3. Usa offload secuencial (menor pico de RAM):

   ```env
   TRYOFF_LOW_VRAM=true
   TRYOFF_OFFLOAD=sequential
   TRYOFF_HEIGHT=512
   TRYOFF_WIDTH=512
   ```

4. Arranca en segundo plano (`-d`) para no perder logs en la terminal; mira `docker compose logs -f tryoff-model` y busca líneas `memory before_inference: VmRSS`.
5. Si Celery reintenta mientras el contenedor reinicia, **pausa jobs** o espera a que el modelo esté `healthy` antes de otra extracción.
6. `restart: on-failure:3` en compose limita bucles de reinicio; si falla 3 veces, revisa RAM antes de `docker compose up tryoff-model` otra vez.

### `GatedRepoError` / 403 en `FLUX.2-klein-base-9B`

- No has aceptado la licencia de la **base** en HF, o el `HF_TOKEN` es de otra cuenta.
- El error **no** significa que falte acceso al LoRA `fal/virtual-tryoff-lora`.

### `Please enable access to public gated repositories` (token fine-grained)

El token **sí** llega al contenedor, pero es **fine-grained** sin permiso para repos gated públicos.

**Opción A (más simple):** crea un token nuevo tipo **Read** (no fine-grained), actualiza `HF_TOKEN` en `backend/.env` y reinicia el contenedor.

**Opción B:** edita el token fine-grained en HF → activa **Access public gated repositories** → guarda → reinicia `tryoff-model`.

Verifica en local (sustituye el repo si hace falta):

```bash
huggingface-cli whoami
python -c "
from huggingface_hub import hf_hub_download
import os
hf_hub_download('black-forest-labs/FLUX.2-klein-base-9B', 'model_index.json', token=os.environ['HF_TOKEN'])
print('OK')
"
```

### `PEFT backend is required for this method`

- Falta el paquete **`peft`** en la imagen Docker (requerido por `load_lora_weights` en diffusers 0.37+).
- Solución: `docker compose --profile gpu build --no-cache tryoff-model` (ya está en `requirements.txt`).

### `infer_schema` / fallo al importar `diffusers`

- Imagen base: PyTorch **2.5.1**+ y `diffusers>=0.37,<0.38` (ver `requirements.txt`). Rebuild sin caché si cambiaste versiones.

### Contenedor reinicia en bucle

- Revisar logs: `docker compose --profile gpu logs tryoff-model`
- Comprobar token: `docker compose --profile gpu run --rm tryoff-model env | grep HF_TOKEN`

## Tests sin GPU

```bash
cd docker/flux && python -m pytest test_main.py -v
```

## Alternativa sin self-hosting de la base BFL

- [fal.ai](https://fal.ai) (API hosted con base + LoRA gestionados por fal).
- Otro proveedor de extracción de prendas con licencia compatible con producción.

## Referencias

- LoRA TryOff: https://huggingface.co/fal/virtual-tryoff-lora  
- Base FLUX.2 klein: https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B  
- Bolt / ADR en repo: `memory-bank/bolts/014-tryoff-model-service/`

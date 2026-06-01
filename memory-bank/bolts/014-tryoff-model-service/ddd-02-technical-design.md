---
unit: 001-tryoff-model-service
bolt: 014-tryoff-model-service
stage: design
status: complete
updated: 2026-05-31T12:30:00Z
---

# Technical Design - TryOff Model Service

## Architecture Pattern

**Hexagonal (Ports & Adapters) — Minimal Variant**

This service is a standalone GPU inference container with a single inbound port (HTTP API). No database, no outbound integrations beyond HuggingFace at build time. The architecture is intentionally flat:

```text
┌─────────────────────────────────────────────────┐
│  Presentation (FastAPI)                         │
│  POST /tryoff · GET /health                     │
├─────────────────────────────────────────────────┤
│  Application (InferenceService)                 │
│  validate → build prompt → run inference        │
├─────────────────────────────────────────────────┤
│  Domain (ModelPipeline, Value Objects)          │
│  Pipeline lifecycle · Prompt templates          │
├─────────────────────────────────────────────────┤
│  Infrastructure (Diffusers, CUDA, Docker)       │
│  FLUX.2-klein + virtual-tryoff-lora on GPU      │
└─────────────────────────────────────────────────┘
```

**Rationale**: Mirrors the FASHN container pattern exactly. The service is a leaf node — no downstream calls, no persistence. Complexity lives in the infrastructure layer (model loading, GPU memory, LoRA fusion).

---

## Layer Structure

### Presentation Layer
- **FastAPI app** with `lifespan` context manager (same as FASHN `main.py`)
- Two endpoints: `POST /tryoff`, `GET /health`
- Request validation via Pydantic models
- Image decoding/encoding via Pillow
- Inference serialization via `asyncio.Lock`

### Application Layer
- **InferenceService**: Orchestrates request validation → prompt building → inference execution → response encoding
- Acquires lock before inference, releases after (ensures single-threaded GPU usage)
- Measures inference time for logging and response metadata

### Domain Layer
- **ModelPipeline**: Wraps `diffusers.FluxPipeline` with fused LoRA
- **PromptBuilder**: Pure function mapping `GarmentType` → prompt string
- **Value Objects**: `GarmentType`, `InferenceParams`, `SourceImage`, `GarmentImage`

### Infrastructure Layer
- **Diffusers library**: `FluxPipeline.from_pretrained()` + `load_lora_weights()` + `fuse_lora()`
- **CUDA runtime**: `torch.bfloat16` dtype on GPU
- **Docker**: NVIDIA CUDA base image, weight download at build time

---

## API Design

### `POST /tryoff` — Garment Extraction Inference

**Request**: `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | Yes | Source image (JPEG or PNG) |
| `garment_type` | str | Yes | `"upper"` \| `"lower"` \| `"dress"` |

**Response**: `image/png` bytes (raw PNG)

**Error Responses**:

| Code | Condition | Body |
|------|-----------|------|
| 400 | Unsupported image format (TIFF, BMP, etc.) | `{"detail": "Unsupported image format. Use JPEG or PNG."}` |
| 413 | Image > 10 MB | `{"detail": "Image exceeds 10 MB size limit."}` |
| 422 | Invalid `garment_type` | `{"detail": "garment_type must be 'upper', 'lower', or 'dress'."}` |
| 503 | GPU OOM during inference | `{"detail": "GPU out of memory. Retry later."}` |
| 504 | Inference timeout (> 120s) | `{"detail": "Inference timed out."}` |

### `GET /health` — Container Health

**Response**: `application/json`

```json
{
  "status": "ok",
  "model_loaded": true,
  "device": "cuda"
}
```

| Code | Condition |
|------|-----------|
| 200 | `model_loaded: true` |
| 503 | `model_loaded: false` (still loading) |

---

## Data Persistence

**None.** This service is entirely stateless:

- Model weights: loaded from Docker volume at startup (read-only after load)
- Input/output images: in-memory only, never persisted
- No database, no cache layer

---

## Security Design

- **Authentication**: None — internal Docker network only (same as FASHN)
- **Authorization**: None — any container on the Docker network can call
- **Input validation**: Pydantic schema validation on garment_type; Pillow format/size check on image
- **Resource limits**: 10 MB image size cap; single inference at a time (lock serialization)

---

## NFR Implementation

- **Performance**: Model loaded once at startup, LoRA fused at load time → zero per-request weight overhead. `torch.bfloat16` for GPU efficiency. Inference p95 target < 60s.
- **Reliability**: Docker `restart: unless-stopped` policy. Container exits with code 1 if model fails to load (no silent failure). Health endpoint for Docker Compose healthcheck.
- **Scalability**: Single-instance by design (one GPU, one inference at a time). Concurrency managed upstream by Celery job queue.

---

## Error Handling

| Error Type | HTTP Code | Response |
|------------|-----------|----------|
| Invalid garment_type | 422 | `{"detail": "garment_type must be 'upper', 'lower', or 'dress'."}` |
| Unsupported image format | 400 | `{"detail": "Unsupported image format. Use JPEG or PNG."}` |
| Image too large (> 10 MB) | 413 | `{"detail": "Image exceeds 10 MB size limit."}` |
| GPU OOM | 503 | `{"detail": "GPU out of memory. Retry later."}` |
| Inference timeout (> 120s) | 504 | `{"detail": "Inference timed out."}` |
| Model not loaded | 503 | `{"detail": "Model is still loading."}` |
| Unexpected error | 500 | `{"detail": "Internal inference error."}` |

---

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| HuggingFace Hub | Download FLUX.2-klein-base-9B + virtual-tryoff-lora weights | Build-time only (HTTPS) |
| NVIDIA GPU | CUDA inference | Runtime (device mount) |

---

## Container Design

### Dockerfile Strategy

**Base image**: `pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime` (same as FASHN)

**Build steps**:
1. System deps: `git`, `curl`
2. Python deps: `diffusers`, `transformers`, `accelerate`, `huggingface_hub`, `fastapi`, `uvicorn`, `pillow`, `safetensors`
3. Copy application files: `main.py`, `requirements.txt`
4. Weight download at build time via `huggingface-cli download`

### Docker Compose Service

```yaml
tryoff-model:
  profiles: ["gpu"]
  build:
    context: ./docker/tryoff-model
    dockerfile: Dockerfile
  env_file:
    - ./backend/.env
  ports:
    - "8003:8000"
  volumes:
    - tryoff_weights:/app/weights
    - tryoff_cache:/app/model_cache
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 300s
  restart: unless-stopped
```

**Key differences from FASHN**:
- Port: `8003:8000` (FASHN is `8002:8000`)
- `start_period: 300s` (FLUX.2-klein is ~18 GB vs FASHN ~2 GB — longer load time)
- Separate named volumes: `tryoff_weights`, `tryoff_cache`

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRYOFF_MODEL_PORT` | `8003` | Host port mapping |
| `TRYOFF_WEIGHTS_DIR` | `/app/weights` | Weight storage directory |
| `TRYOFF_STEPS` | `28` | Diffusion inference steps |
| `TRYOFF_GUIDANCE` | `5.0` | Classifier-free guidance scale |
| `TRYOFF_HEIGHT` | `1024` | Output image height |
| `TRYOFF_WIDTH` | `768` | Output image width |
| `HF_HOME` | `/app/model_cache` | HuggingFace cache directory |

### Makefile Targets

```makefile
docker-tryoff:        # Start TryOff GPU inference server (~24 GB VRAM)
	docker compose --profile gpu up tryoff-model

tryoff-restart:       # Kill orphan process on :8003 and rebuild container
	lsof -ti:8003 | xargs kill -9 2>/dev/null || true
	docker compose --profile gpu up --build -d tryoff-model
	curl -s http://localhost:8003/health

tryoff-test:          # Run inference test against running container
	python docker/tryoff-model/run_test.py
```

---

## Startup Sequence

```text
1. Container starts → uvicorn launches FastAPI app
2. lifespan() enters → calls _load_pipeline()
   a. _ensure_weights() → download from HuggingFace if not cached
   b. FluxPipeline.from_pretrained("black-forest-labs/FLUX.2-klein-base-9B", torch_dtype=torch.bfloat16)
   c. pipeline.load_lora_weights("fal/virtual-tryoff-lora")
   d. pipeline.fuse_lora(lora_scale=1.0)
   e. pipeline.to("cuda")
   f. _model_ready = True
3. lifespan() yields → server accepts requests
4. GET /health returns 200 with model_loaded: true
```

---

## Inference Flow

```text
POST /tryoff (image, garment_type)
  → validate garment_type (upper/lower/dress)
  → validate image format (JPEG/PNG) and size (< 10 MB)
  → decode image to PIL RGB (convert grayscale → RGB)
  → build prompt from garment_type via PromptBuilder
  → acquire asyncio.Lock (serialize inference)
  → run pipeline(prompt, image, params) on GPU
  → encode output to PNG bytes
  → release lock
  → return PNG with Content-Type: image/png
```

---

## File Structure

```text
docker/tryoff-model/
├── Dockerfile
├── main.py              # FastAPI app + lifespan + endpoints
├── requirements.txt     # Python dependencies
└── run_test.py          # Integration test script
```

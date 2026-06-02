"""Servidor de inferencia TryOff — extracción de prendas con virtual-tryoff-lora (fal).

   LoRA de inferencia: fal/virtual-tryoff-lora (Apache-2.0, ~135 MB en HF).
   Base obligatoria (no incluida en el repo del LoRA): FLUX.2-klein-base-9B de BFL.
   Ver https://huggingface.co/fal/virtual-tryoff-lora — fal documenta los dos pasos.

   Pipeline: Flux2KleinPipeline + LoRA fusionado en startup.

   Por qué hace falta la base:
     - Un LoRA solo modifica pesos de un modelo grande ya cargado (~18 GB)
     - ~24 GB VRAM (requiere GPU dedicada, no compartida con FASHN)
     - LoRA fusionado en startup → sin overhead por request
     - Output: prenda sobre fondo blanco, sin partes humanas visibles

   Endpoints:
     POST /tryoff — multipart: image, garment_type → PNG de la prenda extraída
     GET  /health — estado del modelo y disponibilidad

   Variables de entorno:
     TRYOFF_WEIGHTS_DIR — directorio de pesos (default: /app/weights)
     TRYOFF_STEPS       — pasos de difusión (default: 28)
     TRYOFF_GUIDANCE    — escala de classifier-free guidance (default: 5.0)
     TRYOFF_HEIGHT      — alto de la imagen de salida (default: 1024)
     TRYOFF_WIDTH       — ancho de la imagen de salida (default: 768)
     HF_HOME            — directorio de caché de modelos (default: /app/model_cache)
     HF_TOKEN           — token HF para descargar la base gated (no para el LoRA fal)
     TRYOFF_BASE_MODEL  — repo o ruta local de la base (default: FLUX.2-klein-base-9B)
"""

import asyncio
import io
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Literal

logger = logging.getLogger(__name__)

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from PIL import Image

GarmentType = Literal["upper", "lower", "dress"]

_PROMPT_TEMPLATES: dict[str, str] = {
    "upper": "TRYOFF extract the upper garment over a white background, product photography style. NO HUMAN VISIBLE.",
    "lower": "TRYOFF extract the lower garment over a white background, product photography style. NO HUMAN VISIBLE.",
    "dress": "TRYOFF extract the dress/full-body garment over a white background, product photography style. NO HUMAN VISIBLE.",
}

_ALLOWED_FORMATS = {"JPEG", "PNG"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024

_models: dict = {}
_inference_lock = asyncio.Lock()
_model_ready = False

_DEFAULT_BASE_MODEL = "black-forest-labs/FLUX.2-klein-base-9B"
_TRYOFF_LORA_REPO = "fal/virtual-tryoff-lora"
_TRYOFF_LORA_WEIGHT = "virtual-tryoff-lora_diffusers.safetensors"
_TRYOFF_LORA_ADAPTER = "vtoff"


def _hf_token() -> str | None:
    """Token de Hugging Face para repos gated (misma convención que catvton)."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    return token.strip() if token and token.strip() else None


def _base_model_id() -> str:
    return os.environ.get("TRYOFF_BASE_MODEL", _DEFAULT_BASE_MODEL).strip() or _DEFAULT_BASE_MODEL


def _load_pipeline() -> None:
    """Carga base FLUX.2-klein + LoRA fal/virtual-tryoff-lora (mismo flujo que la card de fal)."""
    global _model_ready
    from diffusers import Flux2KleinPipeline

    base_model = _base_model_id()
    hf_token = _hf_token()
    if base_model.startswith("black-forest-labs/") and not hf_token:
        raise RuntimeError(
            f"HF_TOKEN is required to download the gated base model ({base_model}). "
            "fal/virtual-tryoff-lora is only the adapter (~135 MB); it cannot run alone. "
            "Accept the BFL license at "
            f"https://huggingface.co/{base_model} "
            f"(LoRA docs: https://huggingface.co/{_TRYOFF_LORA_REPO})"
        )

    print(f"Loading FLUX.2-klein base ({base_model})…")
    pipe = Flux2KleinPipeline.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        token=hf_token,
    )

    print(f"Loading TryOff LoRA ({_TRYOFF_LORA_REPO})…")
    pipe.load_lora_weights(
        _TRYOFF_LORA_REPO,
        weight_name=_TRYOFF_LORA_WEIGHT,
        adapter_name=_TRYOFF_LORA_ADAPTER,
    )
    pipe.set_adapters(_TRYOFF_LORA_ADAPTER, adapter_weights=1.0)
    pipe.fuse_lora(adapter_names=[_TRYOFF_LORA_ADAPTER], lora_scale=1.0)

    pipe.to("cuda")
    _models["pipe"] = pipe
    _models["device"] = "cuda"
    _model_ready = True
    print("Pipeline loaded and fused. Ready.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación FastAPI."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    build_tag = os.environ.get("TRYOFF_BUILD_TAG", "dev")
    print(f"TryOff container version: {build_tag}")
    try:
        _load_pipeline()
    except Exception as exc:
        from huggingface_hub.errors import GatedRepoError, HfHubHTTPError

        base_model = _base_model_id()
        err_text = str(exc).lower()

        if isinstance(exc, GatedRepoError):
            logger.error(
                "Hugging Face gated base model access denied (%s). "
                "Accept the license at https://huggingface.co/%s with the HF_TOKEN account. "
                "See docker/flux/README.md",
                base_model,
                base_model,
            )
        elif isinstance(exc, HfHubHTTPError) and "public gated" in err_text:
            logger.error(
                "HF_TOKEN is fine-grained but missing 'Access public gated repositories'. "
                "Create a classic Read token or enable that permission in "
                "https://huggingface.co/settings/tokens — then update backend/.env. "
                "Model: %s — see docker/flux/README.md",
                base_model,
            )
        elif "peft backend is required" in err_text:
            logger.error(
                "Missing Python package 'peft' required by diffusers to load LoRA weights. "
                "Rebuild the image after updating docker/flux/requirements.txt."
            )
        else:
            logger.exception("Failed to load FLUX pipeline")
        raise SystemExit(1)
    yield
    _models.clear()


app = FastAPI(title="TryOff garment extraction inference server", lifespan=lifespan)


def _validate_image(data: bytes) -> Image.Image:
    """Valida formato y tamaño de la imagen de entrada."""
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds 10 MB size limit.",
        )
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not decode image. Use JPEG or PNG.",
        )
    if img.format not in _ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format. Use JPEG or PNG.",
        )
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


@app.post("/tryoff")
async def tryoff(
    image: UploadFile = File(..., description="Source image with person (JPEG/PNG)"),
    garment_type: GarmentType = Form(..., description="upper, lower, or dress"),
) -> Response:
    """Extrae una prenda de una foto de persona.

    Recibe una imagen fuente y el tipo de prenda, retorna un PNG
    de la prenda extraída sobre fondo blanco sin partes humanas visibles.
    """
    if not _model_ready:
        raise HTTPException(status_code=503, detail="Model is still loading.")

    raw = await image.read()
    source_img = _validate_image(raw)
    prompt = _PROMPT_TEMPLATES[garment_type]

    steps = int(os.environ.get("TRYOFF_STEPS", "28"))
    guidance = float(os.environ.get("TRYOFF_GUIDANCE", "5.0"))
    height = int(os.environ.get("TRYOFF_HEIGHT", "1024"))
    width = int(os.environ.get("TRYOFF_WIDTH", "768"))

    async with _inference_lock:
        t0 = time.monotonic()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _models["pipe"](
                    prompt=prompt,
                    image=source_img,
                    height=height,
                    width=width,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                ),
            )
        except torch.cuda.OutOfMemoryError:
            logger.error("GPU OOM during inference")
            raise HTTPException(status_code=503, detail="GPU out of memory. Retry later.")
        except TimeoutError:
            logger.error("Inference timed out")
            raise HTTPException(status_code=504, detail="Inference timed out.")
        except Exception:
            logger.exception("Unexpected inference error")
            raise HTTPException(status_code=500, detail="Internal inference error.")

        elapsed_ms = int((time.monotonic() - t0) * 1000)

    output_img = result.images[0]
    buf = io.BytesIO()
    output_img.save(buf, format="PNG")
    payload = buf.getvalue()

    logger.info(
        "tryoff garment_type=%s steps=%d elapsed_ms=%d output=%dx%d bytes=%d",
        garment_type,
        steps,
        elapsed_ms,
        output_img.width,
        output_img.height,
        len(payload),
    )
    return Response(content=payload, media_type="image/png")


@app.get("/health")
async def health() -> JSONResponse:
    """Estado del contenedor y disponibilidad del modelo."""
    status_code = 200 if _model_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if _model_ready else "loading",
            "model_loaded": _model_ready,
            "device": _models.get("device", "unknown"),
        },
    )

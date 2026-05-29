"""FASHN VTON v1.5 inference server.

Model: fashn-ai/fashn-vton-1.5 — maskless virtual try-on in pixel space (MMDiT).
Repo:  https://github.com/fashn-AI/fashn-vton-1.5

Why this model (vs CatVTON-Flux):
  - Maskless / segmentation-free by default: the garment takes its natural form
    instead of being constrained by the silhouette of the clothing the model is
    already wearing (no agnostic-mask engineering required).
  - ~8 GB VRAM (fits easily on a 24 GB TITAN RTX) vs ~24 GB for FLUX-Fill.
  - Categories map 1:1 with our cloth_type (upper/lower/overall).
  - Accepts flat-lay / hanger product shots directly.

Precision: weights ship in bf16 and run in bf16 on Ampere+; on Turing (TITAN RTX)
the pipeline auto-converts to float32 (~4 GB), so no manual flag is needed.

Endpoints:
  POST /predict  — multipart: garment, model; form: cloth_type, garment_photo_type
  POST /classify — multipart: garment → {"cloth_type": "upper"|"lower"|"overall"}
  GET  /health

Environment variables:
  FASHN_WEIGHTS_DIR        — weights directory (default: /app/weights)
  FASHN_STEPS              — diffusion steps; 20=fast 30=balanced 50=quality (default: 30)
  FASHN_GUIDANCE           — classifier-free guidance scale (default: 1.5)
  FASHN_SEED               — RNG seed (default: 42)
  FASHN_GARMENT_PHOTO_TYPE — "flat-lay" (product shot) | "model" (worn) (default: flat-lay)
  FASHN_SEGMENTATION_FREE  — maskless mode (default: true)
  HF_HOME                  — HuggingFace cache (default: /app/model_cache)
"""

import io
import os
from contextlib import asynccontextmanager
from typing import Literal

import torch
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import Response
from PIL import Image

ClothType = Literal["upper", "lower", "overall"]

# cloth_type (our domain) → FASHN category
_CATEGORY_MAP: dict[str, str] = {
    "upper": "tops",
    "lower": "bottoms",
    "overall": "one-pieces",
}

_models: dict = {}


# ---------------------------------------------------------------------------
# Weights + pipeline loading
# ---------------------------------------------------------------------------

def _ensure_weights(weights_dir: str) -> None:
    """Download FASHN + DWPose weights into the cache volume if missing (public, no token)."""
    from huggingface_hub import hf_hub_download

    os.makedirs(weights_dir, exist_ok=True)

    if not os.path.exists(os.path.join(weights_dir, "model.safetensors")):
        print("Downloading FASHN TryOnModel weights…")
        hf_hub_download(
            repo_id="fashn-ai/fashn-vton-1.5",
            filename="model.safetensors",
            local_dir=weights_dir,
        )

    dwpose_dir = os.path.join(weights_dir, "dwpose")
    os.makedirs(dwpose_dir, exist_ok=True)
    for filename in ("yolox_l.onnx", "dw-ll_ucoco_384.onnx"):
        if not os.path.exists(os.path.join(dwpose_dir, filename)):
            print(f"Downloading DWPose/{filename}…")
            hf_hub_download(
                repo_id="fashn-ai/DWPose",
                filename=filename,
                local_dir=dwpose_dir,
            )


def _load_pipeline() -> None:
    from fashn_vton import TryOnPipeline

    weights_dir = os.environ.get("FASHN_WEIGHTS_DIR", "/app/weights")
    _ensure_weights(weights_dir)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # TryOnPipeline auto-selects bf16 (Ampere+) or float32 (Turing/CPU).
    _models["pipe"] = TryOnPipeline(weights_dir=weights_dir, device=device)
    _models["device"] = device


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading FASHN VTON v1.5 pipeline…")
    _load_pipeline()
    print("Ready.")
    yield
    _models.clear()


app = FastAPI(title="FASHN VTON v1.5 inference server", lifespan=lifespan)


@app.post("/predict")
async def predict(
    garment: UploadFile = File(..., description="Garment/clothing image (JPEG)"),
    model: UploadFile = File(..., description="Person/model image (JPEG)"),
    cloth_type: ClothType = Form("upper"),
    garment_photo_type: str = Form(""),
) -> Response:
    garment_img = Image.open(io.BytesIO(await garment.read())).convert("RGB")
    person_img = Image.open(io.BytesIO(await model.read())).convert("RGB")

    category = _CATEGORY_MAP.get(cloth_type, "tops")
    photo_type = (
        garment_photo_type
        or os.environ.get("FASHN_GARMENT_PHOTO_TYPE", "flat-lay")
    )
    seg_free = os.environ.get("FASHN_SEGMENTATION_FREE", "true").lower() == "true"
    steps = int(os.environ.get("FASHN_STEPS", "30"))
    guidance = float(os.environ.get("FASHN_GUIDANCE", "1.5"))
    seed = int(os.environ.get("FASHN_SEED", "42"))

    result = _models["pipe"](
        person_image=person_img,
        garment_image=garment_img,
        category=category,
        garment_photo_type=photo_type,
        num_samples=1,
        num_timesteps=steps,
        guidance_scale=guidance,
        seed=seed,
        segmentation_free=seg_free,
    )

    buf = io.BytesIO()
    result.images[0].save(buf, format="JPEG", quality=95)
    return Response(content=buf.getvalue(), media_type="image/jpeg")


@app.post("/classify")
async def classify(
    garment: UploadFile = File(..., description="Garment/clothing image (JPEG)"),
) -> dict:
    """Zero-shot cloth type (upper | lower | overall) via CLIP."""
    from garment_clip import detect_cloth_type

    return {"cloth_type": detect_cloth_type(await garment.read())}


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "device": _models.get("device", "unknown"),
        "pipeline_loaded": "pipe" in _models,
    }

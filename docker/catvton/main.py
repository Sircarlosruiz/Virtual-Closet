"""CatVTON-Flux inference server.

Models used:
  - xiaozaa/catvton-flux-beta  (FLUX.1-Fill fine-tune, ~24 GB VRAM in bfloat16)
  - mattmdjaga/segformer_b2_clothes  (clothing segmentation for mask generation)

Environment variables:
  HF_TOKEN          — required to download gated FLUX.1-Fill-dev weights
  CATVTON_STEPS     — inference steps (default: 50)
  CATVTON_GUIDANCE  — guidance scale (default: 30.0)
  HF_HOME           — model cache directory (default: /app/model_cache)
"""

import io
import os
import numpy as np
from contextlib import asynccontextmanager
from typing import Literal

import torch
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import Response
from PIL import Image

_models: dict = {}


def _load_segmentation() -> None:
    from transformers import AutoModelForSemanticSegmentation, SegformerImageProcessor

    _models["seg_processor"] = SegformerImageProcessor.from_pretrained(
        "mattmdjaga/segformer_b2_clothes"
    )
    _models["seg_model"] = (
        AutoModelForSemanticSegmentation.from_pretrained(
            "mattmdjaga/segformer_b2_clothes"
        )
        .eval()
        .to("cpu")  # segmentation is fast on CPU
    )


def _load_pipeline() -> None:
    from diffusers import FluxFillPipeline, FluxTransformer2DModel

    hf_token = os.environ.get("HF_TOKEN") or None
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # catvton-flux-beta is only the fine-tuned transformer; base pipeline is FLUX.1-dev.
    transformer = FluxTransformer2DModel.from_pretrained(
        "xiaozaa/catvton-flux-beta",
        torch_dtype=torch.bfloat16,
        token=hf_token,
    )
    pipe = FluxFillPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-dev",
        transformer=transformer,
        torch_dtype=torch.bfloat16,
        token=hf_token,
    )
    # cpu_offload moves layers to GPU only when needed — reduces peak VRAM usage
    if device == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)

    _models["pipe"] = pipe
    _models["device"] = device


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading segmentation model…")
    _load_segmentation()
    print("Loading CatVTON-Flux pipeline…")
    _load_pipeline()
    print("Ready.")
    yield
    _models.clear()


app = FastAPI(title="CatVTON-Flux inference server", lifespan=lifespan)

ClothType = Literal["upper", "lower", "overall"]

# mattmdjaga/segformer_b2_clothes class indices
_CLOTH_CLASSES: dict[str, list[int]] = {
    "upper": [4, 7],       # upper-clothes, dress
    "lower": [5, 6],       # skirt, pants
    "overall": [4, 5, 6, 7],
}


def _get_clothing_mask(image: Image.Image, cloth_type: ClothType) -> Image.Image:
    processor = _models["seg_processor"]
    seg_model = _models["seg_model"]

    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = seg_model(**inputs)

    upsampled = torch.nn.functional.interpolate(
        outputs.logits.cpu(),
        size=(image.height, image.width),
        mode="bilinear",
        align_corners=False,
    )
    pred = upsampled.argmax(dim=1)[0]
    target = torch.tensor(_CLOTH_CLASSES.get(cloth_type, _CLOTH_CLASSES["upper"]))
    mask = torch.isin(pred, target).numpy().astype(np.uint8) * 255
    return Image.fromarray(mask)


def _resize_keep_aspect(img: Image.Image, height: int) -> Image.Image:
    w = max(8, (img.width * height // img.height // 8) * 8)
    return img.resize((w, height), Image.LANCZOS)


def _run_tryon(person: Image.Image, garment: Image.Image, cloth_type: ClothType) -> Image.Image:
    pipe = _models["pipe"]
    target_h = 1024

    person_r = _resize_keep_aspect(person, target_h)
    garment_r = _resize_keep_aspect(garment, target_h)

    # Use the same width for clean concatenation
    w = max(person_r.width, garment_r.width)
    person_r = person_r.resize((w, target_h), Image.LANCZOS)
    garment_r = garment_r.resize((w, target_h), Image.LANCZOS)

    combined_w = w * 2
    combined = Image.new("RGB", (combined_w, target_h))
    combined.paste(person_r, (0, 0))
    combined.paste(garment_r, (w, 0))

    # Mask: clothing region on person = 255 (inpaint), garment side = 0 (keep as reference)
    cloth_mask = _get_clothing_mask(person_r, cloth_type)
    combined_mask = Image.new("L", (combined_w, target_h), 0)
    combined_mask.paste(cloth_mask, (0, 0))

    steps = int(os.environ.get("CATVTON_STEPS", "50"))
    guidance = float(os.environ.get("CATVTON_GUIDANCE", "30.0"))

    result = pipe(
        image=combined,
        mask_image=combined_mask,
        height=target_h,
        width=combined_w,
        num_inference_steps=steps,
        guidance_scale=guidance,
        max_sequence_length=512,
    ).images[0]

    return result.crop((0, 0, w, target_h))


@app.post("/predict")
async def predict(
    garment: UploadFile = File(..., description="Garment/clothing image (JPEG)"),
    model: UploadFile = File(..., description="Person/model image (JPEG)"),
    cloth_type: ClothType = Form("upper"),
) -> Response:
    garment_bytes = await garment.read()
    model_bytes = await model.read()

    person_img = Image.open(io.BytesIO(model_bytes)).convert("RGB")
    garment_img = Image.open(io.BytesIO(garment_bytes)).convert("RGB")

    result = _run_tryon(person_img, garment_img, cloth_type)

    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=95)
    return Response(content=buf.getvalue(), media_type="image/jpeg")


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "device": _models.get("device", "unknown"),
        "models_loaded": [k for k in _models if k not in ("device",)],
    }

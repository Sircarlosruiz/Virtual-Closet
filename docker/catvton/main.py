"""CatVTON-Flux inference server with preprocessing pipeline.

Models used:
  - xiaozaa/catvton-flux-beta  (FLUX.1-Fill fine-tune, ~24 GB VRAM in bfloat16)
  - mattmdjaga/segformer_b2_clothes  (clothing segmentation for mask generation)

Preprocessing steps:
  1. rembg — garment background removal
  2. DWPose — pose validation (frontal check)
  3. Image quality validation (resolution + blur)
  4. Garment normalization (768px height, square padding)

Postprocessing steps:
  5. Face/hair preservation mask (segformer classes 2, 11)
  6. GFPGAN face restoration
  7. Real-ESRGAN upscale (optional, env-controlled)

Environment variables:
  HF_TOKEN          — required to download gated FLUX.1-Fill-dev weights
  CATVTON_STEPS     — inference steps (default: 50)
  CATVTON_GUIDANCE  — guidance scale (default: 30.0)
  HF_HOME           — model cache directory (default: /app/model_cache)
  ENABLE_UPSCALE    — enable 2x Real-ESRGAN upscale (default: false)
"""

import io
import os
import cv2
import numpy as np
from contextlib import asynccontextmanager
from typing import Literal

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

_models: dict = {}


# ---------------------------------------------------------------------------
# Model loaders
# ---------------------------------------------------------------------------

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
        .to("cpu")
    )


def _load_pipeline() -> None:
    from diffusers import FluxFillPipeline, FluxTransformer2DModel

    hf_token = os.environ.get("HF_TOKEN") or None
    device = "cuda" if torch.cuda.is_available() else "cpu"

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
    if device == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)

    _models["pipe"] = pipe
    _models["device"] = device


def _load_pose_model() -> None:
    from controlnet_aux import DWposeDetector

    _models["dwpose"] = DWposeDetector()


def _load_face_restorer() -> None:
    from gfpgan import GFPGANer

    _models["gfpgan"] = GFPGANer(
        model_path="GFPGANv1.4.pth",
        upscale=1,
        arch="clean",
        channel_multiplier=2,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )


def _load_upscaler() -> None:
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    model = RRDBNet(
        num_in_ch=3, num_out_ch=3, num_feat=64,
        num_block=23, num_grow_ch=32, scale=4,
    )
    _models["upscaler"] = RealESRGANer(
        scale=4,
        model_path="RealESRGAN_x4plus.pth",
        model=model,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )


# ---------------------------------------------------------------------------
# Preprocessing functions
# ---------------------------------------------------------------------------

def _remove_garment_background(image: Image.Image) -> Image.Image:
    from rembg import remove, new_session

    session = new_session("birefnet-general")
    result = remove(image, session=session, bgcolor=(255, 255, 255, 255))
    return result.convert("RGB")


def _normalize_garment(image: Image.Image, target_h: int = 768) -> Image.Image:
    w, h = image.size
    scale = target_h / h
    new_w, new_h = int(w * scale), target_h
    image = image.resize((new_w, new_h), Image.LANCZOS)

    size = max(new_w, new_h)
    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    canvas.paste(image, ((size - new_w) // 2, (size - new_h) // 2))
    return canvas


def _get_pose_keypoints(image: Image.Image) -> dict:
    detector = _models.get("dwpose")
    if detector is None:
        return {}
    result = detector(image, include_body=True, include_hand=False, include_face=False)
    keypoints = result.get("bodies", {}).get("candidate", [])
    if not keypoints:
        return {}
    return {
        "shoulder_left": keypoints[5] if len(keypoints) > 5 else None,
        "shoulder_right": keypoints[6] if len(keypoints) > 6 else None,
        "nose": keypoints[0] if len(keypoints) > 0 else None,
    }


def _validate_pose(keypoints: dict) -> tuple[bool, str]:
    sl = keypoints.get("shoulder_left")
    sr = keypoints.get("shoulder_right")
    if sl is None or sr is None:
        return False, "No se detectaron hombros en la imagen del modelo"

    shoulder_width_px = abs(sr[0] - sl[0])
    if shoulder_width_px < 50:
        return False, "Pose lateral detectada — usar foto frontal del modelo"

    return True, "ok"


def _validate_image_quality(image: Image.Image, label: str) -> None:
    if image.width < 256 or image.height < 256:
        raise ValueError(
            f"{label}: resolución mínima es 256x256px, recibido {image.size}"
        )

    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_score < 50:
        raise ValueError(
            f"{label}: imagen demasiado borrosa (score={blur_score:.1f}, mínimo=50)"
        )


# ---------------------------------------------------------------------------
# Postprocessing functions
# ---------------------------------------------------------------------------

def _get_preservation_mask(image: Image.Image) -> Image.Image:
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
    preserve_classes = torch.tensor([2, 11])
    mask = torch.isin(pred, preserve_classes).numpy().astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.dilate(mask, kernel, iterations=2)
    return Image.fromarray(mask)


def _restore_preserved_regions(
    original: Image.Image,
    generated: Image.Image,
    preserve_mask: Image.Image,
) -> Image.Image:
    orig_np = np.array(original.convert("RGB"))
    gen_np = np.array(generated.convert("RGB"))
    mask_np = np.array(preserve_mask)[:, :, None] / 255.0

    mask_blurred = cv2.GaussianBlur(mask_np.squeeze(), (21, 21), 0)[:, :, None]

    result = (orig_np * mask_blurred + gen_np * (1 - mask_blurred)).astype(np.uint8)
    return Image.fromarray(result)


def _restore_face(image: Image.Image, fidelity: float = 0.7) -> Image.Image:
    restorer = _models.get("gfpgan")
    if restorer is None:
        return image

    img_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    _, _, restored_bgr = restorer.enhance(
        img_bgr,
        paste_back=True,
        weight=fidelity,
    )
    return Image.fromarray(cv2.cvtColor(restored_bgr, cv2.COLOR_BGR2RGB))


def _upscale_image(image: Image.Image, scale: int = 2) -> Image.Image:
    upsampler = _models.get("upscaler")
    if upsampler is None:
        return image

    output, _ = upsampler.enhance(np.array(image), outscale=scale)
    return Image.fromarray(output)


# ---------------------------------------------------------------------------
# Core try-on pipeline
# ---------------------------------------------------------------------------

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

    preserve_mask = _get_preservation_mask(person)

    person_r = _resize_keep_aspect(person, target_h)
    garment_r = _resize_keep_aspect(garment, target_h)

    w = max(person_r.width, garment_r.width)
    person_r = person_r.resize((w, target_h), Image.LANCZOS)
    garment_r = garment_r.resize((w, target_h), Image.LANCZOS)

    combined_w = w * 2
    combined = Image.new("RGB", (combined_w, target_h))
    combined.paste(person_r, (0, 0))
    combined.paste(garment_r, (w, 0))

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

    result = result.crop((0, 0, w, target_h))
    result_resized = result.resize(person.size, Image.LANCZOS)

    result_final = _restore_preserved_regions(person, result_resized, preserve_mask)
    result_final = _restore_face(result_final)

    if os.environ.get("ENABLE_UPSCALE", "false").lower() == "true" and "upscaler" in _models:
        result_final = _upscale_image(result_final)

    return result_final


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading segmentation model…")
    _load_segmentation()
    print("Loading CatVTON-Flux pipeline…")
    _load_pipeline()
    print("Loading pose estimation model…")
    _load_pose_model()
    print("Loading face restoration model…")
    _load_face_restorer()
    if os.environ.get("ENABLE_UPSCALE", "false").lower() == "true":
        print("Loading upscaler model…")
        _load_upscaler()
    print("Ready.")
    yield
    _models.clear()


app = FastAPI(title="CatVTON-Flux inference server", lifespan=lifespan)

ClothType = Literal["upper", "lower", "overall"]

_CLOTH_CLASSES: dict[str, list[int]] = {
    "upper": [4, 7],
    "lower": [5, 6],
    "overall": [4, 5, 6, 7],
}


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

    _validate_image_quality(person_img, "Model image")
    _validate_image_quality(garment_img, "Garment image")

    keypoints = _get_pose_keypoints(person_img)
    valid, msg = _validate_pose(keypoints)
    if not valid:
        raise HTTPException(status_code=422, detail=msg)

    garment_img = _remove_garment_background(garment_img)
    garment_img = _normalize_garment(garment_img)

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

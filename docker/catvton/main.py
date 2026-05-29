"""CatVTON-Flux inference server with preprocessing pipeline.

Models used:
  - xiaozaa/catvton-flux-beta  (FLUX.1-Fill fine-tune, ~24 GB VRAM in bfloat16)
  - mattmdjaga/segformer_b2_clothes  (clothing segmentation for mask generation)

Preprocessing steps:
  1. rembg — garment background removal
  2. MediaPipe Pose — pose validation (frontal check)
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
  CATVTON_WIDTH     — try-on panel width  (default: 576, training distribution)
  CATVTON_HEIGHT    — try-on panel height (default: 768, training distribution)
  CATVTON_SEED      — RNG seed for reproducible generations (default: 42)
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

# basicsr (used by gfpgan/realesrgan) imports an internal torchvision module
# removed in torchvision >= 0.15. Register a shim before basicsr is imported.
try:
    import torchvision.transforms.functional_tensor  # noqa: F401
except ModuleNotFoundError:
    import sys
    import types
    from torchvision.transforms.functional import rgb_to_grayscale as _rgb2gray
    _shim = types.ModuleType("torchvision.transforms.functional_tensor")
    _shim.rgb_to_grayscale = _rgb2gray
    sys.modules["torchvision.transforms.functional_tensor"] = _shim

ClothType = Literal["upper", "lower", "overall"]

_CLOTH_CLASSES: dict[str, list[int]] = {
    "upper": [4, 7],       # upper-clothes, dress
    "lower": [5, 6],       # skirt, pants
    "overall": [4, 5, 6, 7],
}

# In-context prompt required by CatVTON-Flux: it tells the transformer that the
# left panel ([IMAGE1]) is the garment and the right panel ([IMAGE2]) is the
# model wearing it. Without this the model has no notion of the try-on task.
_TRYON_PROMPT = (
    "The pair of images highlights a clothing and its styling on a model, "
    "high resolution, 4K, 8K; "
    "[IMAGE1] Detailed product shot of a clothing "
    "[IMAGE2] The same cloth is worn by a model in a lifestyle setting."
)

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
    import mediapipe.solutions.pose as mp_pose

    _models["mp_pose"] = mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        min_detection_confidence=0.5,
    )


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


def _normalize_garment(image: Image.Image, aspect_w: int = 3, aspect_h: int = 4) -> Image.Image:
    """Pad the garment to the try-on panel aspect ratio (default 3:4) on white.

    The garment is later resized to the exact panel size in `_run_tryon`; padding
    here to the same aspect ratio avoids distorting the garment while keeping its
    color signal strong (no large square white border like before).
    """
    w, h = image.size
    target_ratio = aspect_h / aspect_w  # height / width

    if h / w < target_ratio:
        # Too wide → pad vertically.
        new_h = int(round(w * target_ratio))
        canvas = Image.new("RGB", (w, new_h), (255, 255, 255))
        canvas.paste(image, (0, (new_h - h) // 2))
    else:
        # Too tall → pad horizontally.
        new_w = int(round(h / target_ratio))
        canvas = Image.new("RGB", (new_w, h), (255, 255, 255))
        canvas.paste(image, ((new_w - w) // 2, 0))
    return canvas


def _get_pose_keypoints(image: Image.Image) -> dict:
    pose = _models.get("mp_pose")
    if pose is None:
        return {}
    import mediapipe.solutions.pose as mp_pose

    results = pose.process(np.array(image))
    if not results.pose_landmarks:
        return {}
    lm = results.pose_landmarks.landmark
    PL = mp_pose.PoseLandmark
    w, h = image.width, image.height
    return {
        "shoulder_left":  (lm[PL.LEFT_SHOULDER].x * w,  lm[PL.LEFT_SHOULDER].y * h),
        "shoulder_right": (lm[PL.RIGHT_SHOULDER].x * w, lm[PL.RIGHT_SHOULDER].y * h),
        "nose":           (lm[PL.NOSE].x * w,           lm[PL.NOSE].y * h),
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


def _run_tryon(person: Image.Image, garment: Image.Image, cloth_type: ClothType) -> Image.Image:
    pipe = _models["pipe"]

    # Generate at the training distribution (576x768). Higher resolution is
    # obtained afterwards via the optional Real-ESRGAN upscale.
    W = int(os.environ.get("CATVTON_WIDTH", "576"))
    H = int(os.environ.get("CATVTON_HEIGHT", "768"))

    preserve_mask = _get_preservation_mask(person)

    # Both panels are squished to the exact panel size, exactly as the model was
    # trained (no aspect-preserving resize, no forced equal-width distortion).
    person_r = person.resize((W, H), Image.LANCZOS)
    garment_r = garment.resize((W, H), Image.LANCZOS)

    cloth_mask = _get_clothing_mask(person_r, cloth_type)

    # Training order: garment on the LEFT ([IMAGE1]), person on the RIGHT
    # ([IMAGE2]); the inpainting mask covers only the person (right) panel.
    combined_w = W * 2
    combined = Image.new("RGB", (combined_w, H))
    combined.paste(garment_r, (0, 0))
    combined.paste(person_r, (W, 0))

    combined_mask = Image.new("L", (combined_w, H), 0)
    combined_mask.paste(cloth_mask, (W, 0))

    steps = int(os.environ.get("CATVTON_STEPS", "50"))
    guidance = float(os.environ.get("CATVTON_GUIDANCE", "30.0"))
    seed = int(os.environ.get("CATVTON_SEED", "42"))
    generator = torch.Generator(device="cpu").manual_seed(seed)

    result = pipe(
        prompt=_TRYON_PROMPT,
        image=combined,
        mask_image=combined_mask,
        height=H,
        width=combined_w,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
        max_sequence_length=512,
    ).images[0]

    # Keep the RIGHT half (the person wearing the garment).
    result = result.crop((W, 0, combined_w, H))
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
    try:
        _load_pose_model()
        print("Pose estimation model loaded.")
    except Exception as exc:
        print(f"Warning: pose model unavailable ({exc}). Pose validation will be skipped.")
    print("Loading face restoration model…")
    try:
        _load_face_restorer()
        print("Face restoration model loaded.")
    except Exception as exc:
        print(f"Warning: face restorer unavailable ({exc}). Face restoration will be skipped.")
    if os.environ.get("ENABLE_UPSCALE", "false").lower() == "true":
        print("Loading upscaler model…")
        _load_upscaler()
    print("Ready.")
    yield
    _models.clear()


app = FastAPI(title="CatVTON-Flux inference server", lifespan=lifespan)


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

    if "mp_pose" in _models:
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


@app.post("/classify")
async def classify(
    garment: UploadFile = File(..., description="Garment/clothing image (JPEG)"),
) -> dict:
    """Zero-shot cloth type (upper | lower | overall) via CLIP. No GPU required."""
    from garment_clip import detect_cloth_type

    garment_bytes = await garment.read()
    return {"cloth_type": detect_cloth_type(garment_bytes)}


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "device": _models.get("device", "unknown"),
        "models_loaded": [k for k in _models if k not in ("device",)],
    }

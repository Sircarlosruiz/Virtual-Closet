"""Servidor de inferencia FASHN VTON v1.5.

   Modelo: fashn-ai/fashn-vton-1.5 — Virtual try-on sin máscara en espacio de píxeles (MMDiT).
   Repo: https://github.com/fashn-AI/fashn-vton-1.5

   Por qué este modelo (vs CatVTON-Flux):
     - Sin máscara / sin segmentación por defecto: la prenda toma su forma natural
       en lugar de estar limitada por la silueta de la ropa que el modelo ya lleva
       (no requiere ingeniería de máscara agnóstica).
     - ~8 GB VRAM (cabe fácilmente en una TITAN RTX de 24 GB) vs ~24 GB para FLUX-Fill.
     - Las categorías mapean 1:1 con nuestro cloth_type (upper/lower/overall).
     - Acepta fotos de producto en plano/gancho directamente.

   Precisión: los pesos se envían en bf16 y se ejecutan en bf16 en Ampere+; en Turing (TITAN RTX)
   el pipeline convierte automáticamente a float32 (~4 GB), no se necesita flag manual.

   Endpoints:
     POST /predict  — multipart: garment, model; form: cloth_type, garment_photo_type
     POST /classify — multipart: garment → {"cloth_type": "upper"|"lower"|"overall"}
     GET  /health

   Variables de entorno:
     FASHN_WEIGHTS_DIR        — directorio de pesos (default: /app/weights)
     FASHN_STEPS              — pasos de difusión; 20=rápido 30=balanceado 50=calidad (default: 30)
     FASHN_GUIDANCE           — escala de classifier-free guidance (default: 1.5)
     FASHN_SEED               — seed del RNG (default: 42)
     FASHN_GARMENT_PHOTO_TYPE — "flat-lay" (foto producto) | "model" (usada por modelo) (default: flat-lay)
     FASHN_SEGMENTATION_FREE  — modo sin máscara (default: auto — false para one-pieces)
     FASHN_LEG_POSTPROCESS    — fix dark calf artifacts for dresses (default: true)
     FASHN_PRESERVE_LIMBS     — restore hands/arms from original photo (default: true)
     HF_HOME                  — directorio de caché de modelos (default: /app/model_cache)
"""

import hashlib
import io
import logging
import os
from contextlib import asynccontextmanager
from typing import Literal

logger = logging.getLogger(__name__)

import torch
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import Response
from PIL import Image

from postprocess import postprocess_tryon

# Tipo literal para los tipos de prenda soportados
ClothType = Literal["upper", "lower", "overall"]

# Mapa de nuestros tipos de prenda → categorías de FASHN
# FASHN espera categorías específicas: tops, bottoms, one-pieces
_CATEGORY_MAP: dict[str, str] = {
    "upper": "tops",
    "lower": "bottoms",
    "overall": "one-pieces",
}

# Diccionario global para almacenar los modelos cargados
# Se limpia al apagar el servidor para liberar memoria
_models: dict = {}


def _segmentation_free_for(cloth_type: ClothType) -> bool:
    """Determina si usar modo sin máscara para el tipo de prenda dado.
    
    Por defecto es True (máscara libre) para upper/lower. Para one-pieces (overall),
    por defecto es False (usa máscara interna de FASHN) basado en evaluación A/B.
    
    A/B Test Methodology (bolt 012):
    - Run: docker/fashn/ab_segmentation_free.py
    - Compares segmentation_free=True vs False on ≥2 subjects with cloth_type=overall
    - Uses identical FASHN_SEED=42 to isolate the variable
    - Evaluates: dress silhouette accuracy, leg boundary quality, hand region
    
    A/B Result: [TO BE FILLED AFTER RUNNING A/B TEST]
    - Current default: False for overall (garment segmentation ON)
    - Rationale: Heuristic — FASHN's internal garment mask reduces color bleed for one-pieces
    
    Override con variable de entorno FASHN_SEGMENTATION_FREE:
    - "true"/"1"/"yes" → fuerza modo sin máscara
    - "false"/"0"/"no" → fuerza modo con máscara
    """
    raw = os.environ.get("FASHN_SEGMENTATION_FREE", "").strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    # One-pieces benefit from garment segmentation to reduce leg/arm artifacts.
    if cloth_type == "overall":
        return False
    return True


# ---------------------------------------------------------------------------
# Carga de pesos y pipeline
# ---------------------------------------------------------------------------

def _ensure_weights(weights_dir: str) -> None:
    """Descarga los pesos de FASHN y DWPose en el volumen de caché si faltan.
    
    Los modelos son públicos, no requieren token de autenticación.
    Solo descarga si los archivos no existen ya (permite caché persistente).
    """
    from huggingface_hub import hf_hub_download

    os.makedirs(weights_dir, exist_ok=True)

    # Descarga el modelo principal de try-on si no existe
    if not os.path.exists(os.path.join(weights_dir, "model.safetensors")):
        print("Downloading FASHN TryOnModel weights…")
        hf_hub_download(
            repo_id="fashn-ai/fashn-vton-1.5",
            filename="model.safetensors",
            local_dir=weights_dir,
        )

    # Descarga los pesos de DWPose (detección de pose humana para preprocessing)
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
    """Carga el pipeline de FASHN VTON.
    
    Descarga pesos si es necesario, luego inicializa TryOnPipeline.
    Auto-selecciona bf16 para GPU Ampere+ o float32 para Turing/CPU.
    """
    from fashn_vton import TryOnPipeline

    weights_dir = os.environ.get("FASHN_WEIGHTS_DIR", "/app/weights")
    _ensure_weights(weights_dir)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # TryOnPipeline auto-selecciona bf16 (Ampere+) o float32 (Turing/CPU).
    _models["pipe"] = TryOnPipeline(weights_dir=weights_dir, device=device)
    _models["device"] = device


# ---------------------------------------------------------------------------
# Aplicación FastAPI
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación FastAPI."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    build_tag = os.environ.get("FASHN_BUILD_TAG", "dev")
    print(f"FASHN container version: {build_tag}")
    print("Loading FASHN VTON v1.5 pipeline…")
    _load_pipeline()
    print("Ready.")
    yield
    _models.clear()


app = FastAPI(title="FASHN VTON v1.5 inference server", lifespan=lifespan)


@app.post("/predict")
async def predict(
    garment: UploadFile = File(..., description="Imagen de la prenda (JPEG)"),
    model: UploadFile = File(..., description="Imagen de la persona/modelo (JPEG)"),
    cloth_type: ClothType = Form("upper"),
    garment_photo_type: str = Form(""),
) -> Response:
    """Endpoint principal de try-on virtual.
    
    Recibe una imagen de prenda y una imagen del modelo, retorna
    la imagen del modelo usando la prenda especificada.
    
    Args:
        garment: imagen de la prenda (JPEG/PNG)
        model: imagen del modelo/persona (JPEG/PNG)
        cloth_type: tipo de prenda (upper/lower/overall)
        garment_photo_type: tipo de foto ('flat-lay' o 'model')
        
    Returns:
        Imagen JPEG del try-on generado
        
    Proceso:
    1. Decodifica ambas imágenes
    2. Mapea cloth_type a categoría FASHN
    3. Ejecuta pipeline de difusión con parámetros configurables
    4. Aplica post-procesamiento para vestidos (artefactos de piernas)
    5. Retorna imagen JPEG comprimida
    """
    garment_img = Image.open(io.BytesIO(await garment.read())).convert("RGB")
    person_img = Image.open(io.BytesIO(await model.read())).convert("RGB")

    # Determina la categoría de FASHN según el tipo de prenda
    category = _CATEGORY_MAP.get(cloth_type, "tops")
    # Usa el parámetro o la variable de entorno, default 'flat-lay'
    photo_type = (
        garment_photo_type
        or os.environ.get("FASHN_GARMENT_PHOTO_TYPE", "flat-lay")
    )
    seg_free = _segmentation_free_for(cloth_type)
    # Parámetros de generación configurables
    steps = int(os.environ.get("FASHN_STEPS", "30"))
    guidance = float(os.environ.get("FASHN_GUIDANCE", "1.5"))
    seed = int(os.environ.get("FASHN_SEED", "42"))

    # Ejecuta el pipeline de try-on
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

    raw_output = result.images[0]
    output = postprocess_tryon(person_img, raw_output, cloth_type)

    buf = io.BytesIO()
    output.save(buf, format="JPEG", quality=95)
    payload = buf.getvalue()
    logger.info(
        "predict cloth_type=%s seg_free=%s seed=%d raw=%s out=%s bytes=%d",
        cloth_type,
        seg_free,
        seed,
        hashlib.md5(raw_output.tobytes()).hexdigest()[:8],
        hashlib.md5(payload).hexdigest()[:8],
        len(payload),
    )
    return Response(content=payload, media_type="image/jpeg")


@app.post("/classify")
async def classify(
    garment: UploadFile = File(..., description="Imagen de la prenda (JPEG)"),
) -> dict:
    """Clasificador zero-shot del tipo de prenda usando CLIP.
    
    Analiza la imagen de la prenda y determina automáticamente
    si es upper (parte superior), lower (parte inferior), u overall (completa).
    
    Args:
        garment: imagen de la prenda a clasificar
        
    Returns:
        Dict con clave 'cloth_type': 'upper' | 'lower' | 'overall'
    """
    from garment_clip import detect_cloth_type

    return {"cloth_type": detect_cloth_type(await garment.read())}


@app.get("/health")
async def health() -> dict:
    """Endpoint de salud para verificar estado del servicio.
    
    Retorna información sobre el dispositivo (cuda/cpu),
    si el pipeline está cargado, y el estado general.
    """
    return {
        "status": "ok",
        "device": _models.get("device", "unknown"),
        "pipeline_loaded": "pipe" in _models,
    }

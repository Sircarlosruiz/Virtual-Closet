"""Servidor de inferencia CatVTON-Flux con pipeline de pre/post-procesamiento.

   Modelos utilizados:
     - xiaozaa/catvton-flux-beta  (FLUX.1-Fill fine-tune, ~24 GB VRAM en bfloat16)
     - mattmdjaga/segformer_b2_clothes  (segmentación de ropa para generación de máscara)

   Pasos de pre-procesamiento:
     1. rembg — eliminación de fondo de la prenda
     2. MediaPipe Pose — validación de pose (verificar que sea frontal)
     3. Validación de calidad de imagen (resolución + blur)
     4. Normalización de la prenda (768px altura, padding cuadrado)

   Pasos de post-procesamiento:
     5. Máscara de preservación de cara/pelo (clases segformer 2, 11)
     6. Restauración facial con GFPGAN
     7. Upscale con Real-ESRGAN (opcional, controlado por variable de entorno)

   Variables de entorno:
     HF_TOKEN          — requerido para descargar pesos FLUX.1-Fill-dev (gated)
     CATVTON_STEPS     — pasos de inferencia (default: 50)
     CATVTON_GUIDANCE  — escala de guidance (default: 30.0)
     CATVTON_WIDTH     — ancho del panel try-on  (default: 576, distribución de entrenamiento)
     CATVTON_HEIGHT    — alto del panel try-on (default: 768, distribución de entrenamiento)
     CATVTON_SEED      — seed RNG para generaciones reproducibles (default: 42)
     HF_HOME           — directorio de caché de modelos (default: /app/model_cache)
     ENABLE_UPSCALE    — habilitar upscale 2x con Real-ESRGAN (default: false)
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

# Compatibility shim para basicsr (usado por gfpgan/realesrgan).
# basicsr importa torchvision.transforms.functional_tensor que fue removido
# en torchvision >= 0.15. Registramos un shim que provee la función requerida.
try:
    import torchvision.transforms.functional_tensor  # noqa: F401
except ModuleNotFoundError:
    import sys
    import types
    from torchvision.transforms.functional import rgb_to_grayscale as _rgb2gray
    _shim = types.ModuleType("torchvision.transforms.functional_tensor")
    _shim.rgb_to_grayscale = _rgb2gray
    sys.modules["torchvision.transforms.functional_tensor"] = _shim

# Tipo literal para categorías de prenda soportadas
ClothType = Literal["upper", "lower", "overall"]

# Mapeo de categorías de prenda → IDs de clase del segformer para masks
# El segformer numera las clases de segmentación de ropa
_CLOTH_CLASSES: dict[str, list[int]] = {
    "upper": [4, 7],       # upper-clothes (ropa superior), dress (vestido)
    "lower": [5, 6],        # skirt (falda), pants (pantalones)
    "overall": [4, 5, 6, 7], # incluye todas las clases para vestidos completos
}

# Prompt requerido por CatVTON-Flux: indica al transformador que el panel
# izquierdo ([IMAGE1]) es la prenda y el panel derecho ([IMAGE2]) es el
# modelo usándola. Sin esto el modelo no tiene noción de la tarea de try-on.
# Este prompt está embebido en los pesos del modelo y es necesario para
# que la generación funcione correctamente.
_TRYON_PROMPT = (
    "The pair of images highlights a clothing and its styling on a model, "
    "high resolution, 4K, 8K; "
    "[IMAGE1] Detailed product shot of a clothing "
    "[IMAGE2] The same cloth is worn by a model in a lifestyle setting."
)

# Diccionario global para almacenar modelos cargados
_models: dict = {}


# ---------------------------------------------------------------------------
# Cargadores de modelos
# ---------------------------------------------------------------------------

def _load_segmentation() -> None:
    """Carga el modelo Segformer para segmentación de ropa.
    
    Carga procesador e modelo de segmentación semántica que identifica
    diferentes clases de ropa en la imagen (upper-clothes, dress, skirt, pants).
    Se ejecuta en CPU para no ocupar VRAM.
    """
    from transformers import AutoModelForSemanticSegmentation, SegformerImageProcessor

    # Carga procesador y modelo desde Hugging Face
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
    """Carga el pipeline principal CatVTON-Flux para try-on.
    
    Utiliza FLUX.1-Dev como base con el transformer CatVTON fine-tuneado.
    Requiere token de Hugging Face para descargar los pesos (modelo gated).
    Ejecuta en bfloat16 para optimizar VRAM.
    
    En GPU: usa model CPU offload para compartir VRAM entre modelos.
    En CPU: mueve el pipeline completo a memoria RAM.
    """
    from diffusers import FluxFillPipeline, FluxTransformer2DModel

    hf_token = os.environ.get("HF_TOKEN") or None
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Carga el transformer fine-tuneado de CatVTON
    transformer = FluxTransformer2DModel.from_pretrained(
        "xiaozaa/catvton-flux-beta",
        torch_dtype=torch.bfloat16,
        token=hf_token,
    )
    # Carga el pipeline base de FLUX.1-Dev
    pipe = FluxFillPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-dev",
        transformer=transformer,
        torch_dtype=torch.bfloat16,
        token=hf_token,
    )
    if device == "cuda":
        # Offload inteligente para compartir VRAM
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)

    _models["pipe"] = pipe
    _models["device"] = device


def _load_pose_model() -> None:
    """Carga el modelo de estimación de pose de MediaPipe.
    
    Usa MediaPipe Pose para validar que la foto del modelo
    sea frontal (detección de ambos hombros).
    
    Configuración:
    - static_image_mode=True: optimizado para imágenes individuales
    - model_complexity=1: balance entre speed/accuracy
    - min_detection_confidence=0.5: umbral para detección válida
    """
    import mediapipe.solutions.pose as mp_pose

    _models["mp_pose"] = mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        min_detection_confidence=0.5,
    )


def _load_face_restorer() -> None:
    """Carga el modelo GFPGAN para restauración facial.
    
    GFPGAN restaura rostros degradados en las imágenes generadas.
    Usa arquitectura "clean" con channel_multiplier=2 para mejor calidad.
    
    El modelo se descarga automáticamente si no está en caché.
    """
    from gfpgan import GFPGANer

    _models["gfpgan"] = GFPGANer(
        model_path="GFPGANv1.4.pth",
        upscale=1,
        arch="clean",
        channel_multiplier=2,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )


def _load_upscaler() -> None:
    """Carga el modelo Real-ESRGAN para upscaling de imagen.
    
    Real-ESRGAN_x4plus puede aumentar la resolución 4x manteniendo calidad.
    Usa arquitectura RRDB (Residual-in-Residual Dense Block).
    
    Solo se carga si ENABLE_UPSCALE=true, ya que consume recursos significativos.
    """
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    # Define arquitectura del modelo Real-ESRGAN
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
# Funciones de pre-procesamiento
# ---------------------------------------------------------------------------

def _remove_garment_background(image: Image.Image) -> Image.Image:
    """Elimina el fondo de la imagen de la prenda usando rembg.
    
    Usa el modelo BiRefNet-general para segmentación precisa del objeto
    y eliminar todo el fondo. Reemplaza fondo por blanco (RGBA → RGB).
    
    Args:
        image: imagen PIL de la prenda con fondo
        
    Returns:
        Imagen PIL con fondo eliminado y fondo blanco
    """
    from rembg import remove, new_session

    session = new_session("birefnet-general")
    result = remove(image, session=session, bgcolor=(255, 255, 255, 255))
    return result.convert("RGB")


def _normalize_garment(image: Image.Image, aspect_w: int = 3, aspect_h: int = 4) -> Image.Image:
    """Normaliza la prenda al ratio de aspecto del panel try-on con padding blanco.

    Calcula el ratio objetivo (default 3:4) y añade padding blanco
    donde sea necesario para alcanzar ese ratio sin distorsionar la prenda.

    La prenda se redimensiona después al tamaño exacto del panel en _run_tryon;
    este padding previo evita distorsión mientras mantiene la señal de color fuerte
    (sin bordes blancos cuadrados excesivos).

    Args:
        image: imagen de la prenda procesada
        aspect_w: ancho del ratio objetivo (default 3)
        aspect_h: alto del ratio objetivo (default 4)
        
    Returns:
        Imagen con padding blanco al ratio de aspecto especificado
    """
    w, h = image.size
    target_ratio = aspect_h / aspect_w  # height / width

    if h / w < target_ratio:
        # Imagen muy ancha → padding vertical arriba/abajo
        new_h = int(round(w * target_ratio))
        canvas = Image.new("RGB", (w, new_h), (255, 255, 255))
        canvas.paste(image, (0, (new_h - h) // 2))
    else:
        # Imagen muy alta → padding horizontal izquierda/derecha
        new_w = int(round(h / target_ratio))
        canvas = Image.new("RGB", (new_w, h), (255, 255, 255))
        canvas.paste(image, ((new_w - w) // 2, 0))
    return canvas


def _get_pose_keypoints(image: Image.Image) -> dict:
    """Extrae keypoints de pose desde la imagen usando MediaPipe.
    
    Detecta los puntos de referencia de pose más importantes para
    la validación de pose frontal: hombros y nariz.
    
    Args:
        image: imagen PIL de la persona/modelo
        
    Returns:
        Diccionario con coordenadas (x, y) de shoulder_left, shoulder_right, nose
        o diccionario vacío si no se detectan landmarks
    """
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
        # Coordenadas normalizadas (0-1) convertidas a pixels
        "shoulder_left":  (lm[PL.LEFT_SHOULDER].x * w,  lm[PL.LEFT_SHOULDER].y * h),
        "shoulder_right": (lm[PL.RIGHT_SHOULDER].x * w, lm[PL.RIGHT_SHOULDER].y * h),
        "nose":           (lm[PL.NOSE].x * w,           lm[PL.NOSE].y * h),
    }


def _validate_pose(keypoints: dict) -> tuple[bool, str]:
    """Valida que la pose del modelo sea frontal y apta para try-on.
    
    Criterios:
    - Deben detectarse ambos hombros (la pose no es lateral)
    - La distancia entre hombros debe ser >= 50px (no es pose parcial)
    
    Args:
        keypoints: diccionario con coordenadas de hombros y nariz
        
    Returns:
        Tupla (es_válido, mensaje) donde mensaje describe el error si no es válido
    """
    sl = keypoints.get("shoulder_left")
    sr = keypoints.get("shoulder_right")
    if sl is None or sr is None:
        return False, "No se detectaron hombros en la imagen del modelo"

    shoulder_width_px = abs(sr[0] - sl[0])
    if shoulder_width_px < 50:
        return False, "Pose lateral detectada — usar foto frontal del modelo"

    return True, "ok"


def _validate_image_quality(image: Image.Image, label: str) -> None:
    """Valida que la imagen cumpla requisitos mínimos de calidad.
    
    Checks:
    - Resolución mínima: 256x256 pixels
    - Nitidez: score Laplacian >= 50 (imagen no demasiado borrosa)
    
    Args:
        image: imagen PIL a validar
        label: etiqueta para mensaje de error (ej: "Model image", "Garment image")
        
    Raises:
        ValueError: si la imagen no cumple los requisitos
    """
    # Validación de resolución
    if image.width < 256 or image.height < 256:
        raise ValueError(
            f"{label}: resolución mínima es 256x256px, recibido {image.size}"
        )

    # Validación de nitidez usando varianza del Laplaciano
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_score < 50:
        raise ValueError(
            f"{label}: imagen demasiado borrosa (score={blur_score:.1f}, mínimo=50)"
        )


# ---------------------------------------------------------------------------
# Funciones de post-procesamiento
# ---------------------------------------------------------------------------

def _get_preservation_mask(image: Image.Image) -> Image.Image:
    """Genera máscara para preservar cara y pelo en la imagen generada.
    
    Usa Segformer para segmentar la imagen y extraer las clases
    2 (hair) y 11 (face). Estas regiones se preservan de la imagen
    original para evitar que la IA modifique la apariencia del modelo.
    
    Args:
        image: imagen PIL del modelo original
        
    Returns:
        Máscara binaria (0/255) donde 255 = preservar, 0 = generar
    """
    processor = _models["seg_processor"]
    seg_model = _models["seg_model"]

    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = seg_model(**inputs)

    # Re-escala logits al tamaño original de la imagen
    upsampled = torch.nn.functional.interpolate(
        outputs.logits.cpu(),
        size=(image.height, image.width),
        mode="bilinear",
        align_corners=False,
    )
    pred = upsampled.argmax(dim=1)[0]
    # Extrae solo las clases 2 (face) y 11 (hair)
    preserve_classes = torch.tensor([2, 11])
    mask = torch.isin(pred, preserve_classes).numpy().astype(np.uint8) * 255

    # Dilata la máscara para incluir bordes suave
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.dilate(mask, kernel, iterations=2)
    return Image.fromarray(mask)


def _restore_preserved_regions(
    original: Image.Image,
    generated: Image.Image,
    preserve_mask: Image.Image,
) -> Image.Image:
    """Restaura regiones preservadas (cara/pelo) en la imagen generada.
    
    Aplica un blur gaussiano a la máscara para suavizar bordes
    y mezcla la imagen original con la generada según la máscara.
    
    Args:
        original: imagen original del modelo
        generated: imagen generada por el pipeline
        preserve_mask: máscara de regiones a preservar de la original
        
    Returns:
        Imagen con regiones preservadas mezcladas desde la original
    """
    orig_np = np.array(original.convert("RGB"))
    gen_np = np.array(generated.convert("RGB"))
    mask_np = np.array(preserve_mask)[:, :, None] / 255.0

    # Blur gaussiano para suavizar transiciones de la máscara
    mask_blurred = cv2.GaussianBlur(mask_np.squeeze(), (21, 21), 0)[:, :, None]

    # Blending: original * máscara + generado * (1 - máscara)
    result = (orig_np * mask_blurred + gen_np * (1 - mask_blurred)).astype(np.uint8)
    return Image.fromarray(result)


def _restore_face(image: Image.Image, fidelity: float = 0.7) -> Image.Image:
    """Restaura y mejora el rostro usando GFPGAN.
    
    GFPGAN mejora la calidad del rostro en la imagen generada,
    corrigiendo artefactos comunes de modelos de difusión.
    
    Args:
        image: imagen PIL con rostro
        fidelity: peso de mezcla (0=pura restaurada, 1=pura original), default 0.7
        
    Returns:
        Imagen con rostro mejorado
    """
    restorer = _models.get("gfpgan")
    if restorer is None:
        return image

    # Convierte RGB → BGR para GFPGAN (formato OpenCV)
    img_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    _, _, restored_bgr = restorer.enhance(
        img_bgr,
        paste_back=True,  # pega la cara restaurada sobre fondo original
        weight=fidelity,  # controla fidelidad a la cara original
    )
    # Convierte BGR → RGB para retornar
    return Image.fromarray(cv2.cvtColor(restored_bgr, cv2.COLOR_BGR2RGB))


def _upscale_image(image: Image.Image, scale: int = 2) -> Image.Image:
    """Escala la imagen usando Real-ESRGAN.
    
    Upscaling de alta calidad que preserva detalles y reduce artifacts.
    
    Args:
        image: imagen PIL a escalar
        scale: factor de escala (default 2x)
        
    Returns:
        Imagen escalada al nuevo tamaño
    """
    upsampler = _models.get("upscaler")
    if upsampler is None:
        return image

    output, _ = upsampler.enhance(np.array(image), outscale=scale)
    return Image.fromarray(output)


# ---------------------------------------------------------------------------
# Pipeline core de try-on
# ---------------------------------------------------------------------------

def _get_clothing_mask(image: Image.Image, cloth_type: ClothType) -> Image.Image:
    """Genera máscara de la ropa que lleva el modelo en la imagen.
    
    Usa Segformer para segmentar y extraer solo las clases de ropa
    correspondientes al tipo de prenda solicitado.
    
    Args:
        image: imagen PIL del modelo (debe tener el tamaño del panel WxH)
        cloth_type: tipo de prenda a segmentar
        
    Returns:
        Máscara binaria (0/255) donde 255 = pixels de ropa a reemplazar
    """
    processor = _models["seg_processor"]
    seg_model = _models["seg_model"]

    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = seg_model(**inputs)

    # Re-escala al tamaño del panel
    upsampled = torch.nn.functional.interpolate(
        outputs.logits.cpu(),
        size=(image.height, image.width),
        mode="bilinear",
        align_corners=False,
    )
    pred = upsampled.argmax(dim=1)[0]
    # Obtiene las clases objetivo según el tipo de prenda
    target = torch.tensor(_CLOTH_CLASSES.get(cloth_type, _CLOTH_CLASSES["upper"]))
    mask = torch.isin(pred, target).numpy().astype(np.uint8) * 255
    return Image.fromarray(mask)


def _run_tryon(person: Image.Image, garment: Image.Image, cloth_type: ClothType) -> Image.Image:
    """Ejecuta el pipeline completo de try-on virtual.
    
    Pasos:
    1. Genera máscara de preservación (cara/pelo)
    2. Redimensiona ambas imágenes al tamaño del panel (576x768)
    3. Genera máscara de ropa del modelo
    4. Combina garment + modelo en una imagen doble (panel izquierdo + derecho)
    5. Ejecuta inferencia FLUX con la máscara de inpainting
    6. Extrae la mitad derecha (modelo con nueva prenda)
    7. Redimensiona al tamaño original
    8. Restaura regiones preservadas (cara/pelo)
    9. Restaura rostro con GFPGAN
    10. Upscale opcional con Real-ESRGAN
    
    Args:
        person: imagen PIL del modelo
        garment: imagen PIL de la prenda (pre-procesada)
        cloth_type: tipo de prenda (upper/lower/overall)
        
    Returns:
        Imagen final del try-on
    """
    pipe = _models["pipe"]

    # Genera a la resolución de entrenamiento del modelo (576x768).
    # Mayor resolución se obtiene después con Real-ESRGAN.
    W = int(os.environ.get("CATVTON_WIDTH", "576"))
    H = int(os.environ.get("CATVTON_HEIGHT", "768"))

    # Genera máscara de preservación de cara/pelo
    preserve_mask = _get_preservation_mask(person)

    # Redimensiona ambas imágenes al tamaño exacto del panel,
    # exactamente como fue entrenado el modelo (sin mantener aspect ratio).
    person_r = person.resize((W, H), Image.LANCZOS)
    garment_r = garment.resize((W, H), Image.LANCZOS)

    # Genera máscara de la ropa actual del modelo
    cloth_mask = _get_clothing_mask(person_r, cloth_type)

    # Combina en imagen doble: garment izquierda ([IMAGE1]), modelo derecha ([IMAGE2]).
    # El modelo fue entrenado con este layout específico.
    combined_w = W * 2
    combined = Image.new("RGB", (combined_w, H))
    combined.paste(garment_r, (0, 0))
    combined.paste(person_r, (W, 0))

    # La máscara solo cubre el panel derecho (donde está el modelo)
    combined_mask = Image.new("L", (combined_w, H), 0)
    combined_mask.paste(cloth_mask, (W, 0))

    # Parámetros de generación configurables
    steps = int(os.environ.get("CATVTON_STEPS", "50"))
    guidance = float(os.environ.get("CATVTON_GUIDANCE", "30.0"))
    seed = int(os.environ.get("CATVTON_SEED", "42"))
    generator = torch.Generator(device="cpu").manual_seed(seed)

    # Ejecuta el pipeline de difusión
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

    # Extrae solo la mitad derecha (modelo usando la prenda)
    result = result.crop((W, 0, combined_w, H))
    result_resized = result.resize(person.size, Image.LANCZOS)

    # Post-procesamiento: restaura cara/pelo y mejora rostro
    result_final = _restore_preserved_regions(person, result_resized, preserve_mask)
    result_final = _restore_face(result_final)

    # Upscale opcional si está habilitado
    if os.environ.get("ENABLE_UPSCALE", "false").lower() == "true" and "upscaler" in _models:
        result_final = _upscale_image(result_final)

    return result_final


# ---------------------------------------------------------------------------
# Aplicación FastAPI
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: carga todos los modelos al iniciar.
    
    Modelos cargados en orden:
    1. Segmentation (Segformer) - CPU
    2. Pipeline principal (CatVTON-Flux) - GPU/CPU
    3. Pose estimation (MediaPipe) - CPU
    4. Face restorer (GFPGAN) - GPU/CPU
    5. Upscaler (Real-ESRGAN) - solo si ENABLE_UPSCALE=true
    
    Cada modelo es opcional si falla la carga (excepto segmentation y pipeline).
    Al cerrar, limpia todos los modelos de memoria.
    """
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
    garment: UploadFile = File(..., description="Imagen de la prenda (JPEG)"),
    model: UploadFile = File(..., description="Imagen de la persona/modelo (JPEG)"),
    cloth_type: ClothType = Form("upper"),
) -> Response:
    """Endpoint principal de try-on virtual.
    
    Recibe imagen de prenda y modelo, retorna imagen del modelo usando la prenda.
    
    Flujo completo:
    1. Lee y decodifica ambas imágenes
    2. Valida calidad de imagen (resolución, nitidez)
    3. Valida pose del modelo (debe ser frontal)
    4. Pre-procesa la prenda (elimina fondo, normaliza)
    5. Ejecuta pipeline de try-on
    6. Retorna imagen JPEG del resultado
    
    Args:
        garment: imagen de la prenda (JPEG)
        model: imagen del modelo (JPEG)
        cloth_type: tipo de prenda (upper/lower/overall)
        
    Returns:
        Imagen JPEG del try-on generado
        
    Raises:
        HTTPException 422: si la pose no es válida o las imágenes no cumplen requisitos
    """
    garment_bytes = await garment.read()
    model_bytes = await model.read()

    person_img = Image.open(io.BytesIO(model_bytes)).convert("RGB")
    garment_img = Image.open(io.BytesIO(garment_bytes)).convert("RGB")

    # Valida calidad de ambas imágenes
    _validate_image_quality(person_img, "Model image")
    _validate_image_quality(garment_img, "Garment image")

    # Valida que el modelo tenga pose frontal
    if "mp_pose" in _models:
        keypoints = _get_pose_keypoints(person_img)
        valid, msg = _validate_pose(keypoints)
        if not valid:
            raise HTTPException(status_code=422, detail=msg)

    # Pre-procesa la prenda: elimina fondo y normaliza
    garment_img = _remove_garment_background(garment_img)
    garment_img = _normalize_garment(garment_img)

    # Ejecuta el pipeline de try-on
    result = _run_tryon(person_img, garment_img, cloth_type)

    # Codifica y retorna resultado como JPEG
    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=95)
    return Response(content=buf.getvalue(), media_type="image/jpeg")


@app.post("/classify")
async def classify(
    garment: UploadFile = File(..., description="Imagen de la prenda (JPEG)"),
) -> dict:
    """Clasificador zero-shot del tipo de prenda usando CLIP.
    
    A diferencia de /predict, este endpoint no requiere GPU
    ya que CLIP es liviano y puede ejecutarse en CPU.
    
    Args:
        garment: imagen de la prenda a clasificar
        
    Returns:
        Dict con clave 'cloth_type': 'upper' | 'lower' | 'overall'
    """
    from garment_clip import detect_cloth_type

    garment_bytes = await garment.read()
    return {"cloth_type": detect_cloth_type(garment_bytes)}


@app.get("/health")
async def health() -> dict:
    """Endpoint de salud para verificar estado del servicio.
    
    Retorna:
    - status: siempre "ok" si el servidor responde
    - device: cuda o cpu según disponibilidad
    - models_loaded: lista de modelos cargados (sin device)
    """
    return {
        "status": "ok",
        "device": _models.get("device", "unknown"),
        "models_loaded": [k for k in _models if k not in ("device",)],
    }

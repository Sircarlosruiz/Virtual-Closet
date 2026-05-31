"""Clasificador de tipo de prenda zero-shot usando CLIP (se ejecuta dentro del contenedor GPU).
   
   Este módulo utiliza el modelo CLIP de OpenAI para clasificar automáticamente
   una imagen de prenda en una de tres categorías: 'upper' (parte superior),
   'lower' (parte inferior) o 'overall' (prenda completa como vestidos).
   
   Categorías soportadas:
   - upper: camisa, blusa, top, chaqueta, sweater, hoodie
   - lower: pantalones, falda, shorts, jeans, pantalones formales
   - overall: vestido, enterizo, rompero, overoles
   
   Si CLIP no está disponible, utiliza un fallback heurístico basado en
   la proporción aspect ratio de la imagen para inferir el tipo de prenda.
"""

from __future__ import annotations

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

# Definición de etiquetas para clasificación zero-shot de CLIP.
# Cada tipo de prenda tiene palabras clave asociadas que CLIP usa
# para comparar con la imagen del garments.
_LABELS: dict[str, list[str]] = {
    "upper": ["shirt", "blouse", "top", "jacket", "sweater", "hoodie"],
    "lower": ["pants", "skirt", "shorts", "jeans", "trousers"],
    "overall": ["dress", "jumpsuit", "romper", "overalls"],
}

# Variables globales para almacenar el modelo y procesador CLIP cargados.
# Se inicializan lazily para evitar cargar el modelo en cada llamada.
_clip_model = None
_clip_processor = None


def _heuristic_cloth_type(image: Image.Image) -> str:
    """Método fallback cuando CLIP no está disponible: infiere el tipo de prenda
    a partir de la proporción de aspecto de la imagen.
    
    Lógica:
    - Si height/width >= 1.25: la imagen es más alta que ancha (vertical),
      típicamente vestido/overall
    - Si height/width >= 0.95: imagen casi cuadrada, típicamente upper
    - De lo contrario: imagen horizontal (más ancha que alta), típicamente lower
    """
    w, h = image.size
    ratio = h / max(w, 1)
    if ratio >= 1.25:
        return "overall"
    if ratio >= 0.95:
        return "upper"
    return "lower"


def _get_clip():
    """Carga lazy del modelo y procesador CLIP.
    
    Utiliza safetensors en lugar de torch.load para evitar vulnerabilidades
    CVE en torch < 2.6 que podrían estar presentes en la imagen base.
    El modelo CLIP se descarga desde huggingface si no está en caché.
    """
    global _clip_model, _clip_processor
    if _clip_model is None:
        from transformers import CLIPModel, CLIPProcessor

        # safetensors evita el CVE de torch.load en torch<2.6 en la imagen base.
        _clip_model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32",
            use_safetensors=True,
        )
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _clip_model, _clip_processor


def _detect_via_clip(garment_bytes: bytes) -> str:
    """Detecta el tipo de prenda usando el modelo CLIP.
    
    Proceso:
    1. Decodifica los bytes de la imagen
    2. Prepara los inputs con todas las etiquetas de texto y la imagen
    3. Ejecuta inferencia con torch.no_grad() para eficiencia
    4. Obtiene probabilidades y selecciona la mejor etiqueta
    5. Mapea la etiqueta a una categoría (upper/lower/overall)
    
    Args:
        garment_bytes: bytes de la imagen de la prenda en JPEG/PNG
        
    Returns:
        Tipo de prenda: 'upper' | 'lower' | 'overall'
    """
    import torch

    model, processor = _get_clip()

    # Convierte bytes a imagen PIL y normaliza a RGB
    image = Image.open(io.BytesIO(garment_bytes)).convert("RGB")
    # Genera lista plana de todas las etiquetas para CLIP
    all_labels = [label for labels in _LABELS.values() for label in labels]

    # Prepara inputs: texto con etiquetas e imagen de la prenda
    inputs = processor(
        text=all_labels, images=image, return_tensors="pt", padding=True
    )

    with torch.no_grad():
        outputs = model(**inputs)
        # logits_per_image contiene las puntuaciones de similitud imagen-texto
        # softmax para convertir a probabilidades normalizadas
        probs = outputs.logits_per_image.softmax(dim=1)[0]

    # Obtiene la etiqueta con mayor probabilidad
    best_label = all_labels[int(probs.argmax().item())]
    # Busca a qué categoría pertenece la etiqueta ganadora
    for cloth_type, labels in _LABELS.items():
        if best_label in labels:
            return cloth_type
    return "upper"  # default si no hay match


def detect_cloth_type(garment_bytes: bytes) -> str:
    """Función principal de clasificación de tipo de prenda.
    
    Intenta usar CLIP primero; si falla por cualquier razón (modelo no disponible,
    imagen corrupta, etc.), usa el fallback heurístico basado en aspect ratio.
    
    Args:
        garment_bytes: bytes de la imagen de la prenda
        
    Returns:
        Tipo de prenda: 'upper' | 'lower' | 'overall'
    """
    try:
        return _detect_via_clip(garment_bytes)
    except Exception as exc:
        # Fallback: intenta clasificar por aspect ratio
        image = Image.open(io.BytesIO(garment_bytes)).convert("RGB")
        result = _heuristic_cloth_type(image)
        logger.warning("CLIP classify failed (%s); heuristic=%s", exc, result)
        return result

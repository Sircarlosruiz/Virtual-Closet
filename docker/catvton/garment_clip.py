"""Clasificador de tipo de prenda zero-shot usando CLIP (se ejecuta solo en el contenedor GPU).
   
   Este módulo utiliza el modelo CLIP de OpenAI para clasificar automáticamente
   una imagen de prenda en una de tres categorías: 'upper', 'lower' o 'overall'.
   
   A diferencia de FASHN, este clasificador no tiene fallback heurístico —
   CLIP es requerido y debe estar disponible en el contenedor.
   
   Categorías soportadas:
   - upper: camisa, blusa, top, chaqueta, sweater, hoodie
   - lower: pantalones, falda, shorts, jeans, pantalones formales
   - overall: vestido, enterizo, rompero, overoles
"""

from __future__ import annotations

import io

from PIL import Image

# Definición de etiquetas para clasificación zero-shot de CLIP.
# Cada tipo de prenda tiene palabras clave asociadas para comparar con la imagen.
_LABELS: dict[str, list[str]] = {
    "upper": ["shirt", "blouse", "top", "jacket", "sweater", "hoodie"],
    "lower": ["pants", "skirt", "shorts", "jeans", "trousers"],
    "overall": ["dress", "jumpsuit", "romper", "overalls"],
}

# Modelo y procesador CLIP cargados lazily para evitar overhead al importar
_clip_model = None
_clip_processor = None


def _get_clip():
    """Carga lazy del modelo y procesador CLIP desde Hugging Face.
    
    Descarga el modelo 'clip-vit-base-patch32' de OpenAI si no está en caché.
    Se inicializa una sola vez y se reutiliza en llamadas posteriores.
    """
    global _clip_model, _clip_processor
    if _clip_model is None:
        from transformers import CLIPModel, CLIPProcessor

        # Carga modelo y procesador de CLIP
        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _clip_model, _clip_processor


def detect_cloth_type(garment_bytes: bytes) -> str:
    """Clasifica el tipo de prenda usando CLIP zero-shot classification.
    
    Proceso:
    1. Carga el modelo CLIP si no está cargado
    2. Convierte bytes a imagen PIL en RGB
    3. Genera lista de todas las etiquetas de texto
    4. Prepara inputs con texto e imagen
    5. Ejecuta inferencia con softmax para obtener probabilidades
    6. Selecciona la etiqueta con mayor probabilidad
    7. Mapea la etiqueta a una categoría (upper/lower/overall)
    
    Args:
        garment_bytes: bytes de la imagen de la prenda (JPEG/PNG)
        
    Returns:
        Tipo de prenda: 'upper' | 'lower' | 'overall'
    """
    import torch

    model, processor = _get_clip()

    # Convierte bytes a imagen PIL
    image = Image.open(io.BytesIO(garment_bytes)).convert("RGB")
    # Genera lista plana de todas las etiquetas para comparación
    all_labels = [label for labels in _LABELS.values() for label in labels]

    # Prepara inputs: etiquetas de texto y imagen de la prenda
    inputs = processor(
        text=all_labels, images=image, return_tensors="pt", padding=True
    )

    with torch.no_grad():
        outputs = model(**inputs)
        # softmax para convertir puntuaciones a probabilidades normalizadas
        probs = outputs.logits_per_image.softmax(dim=1)[0]

    # Obtiene la etiqueta con mayor probabilidad
    best_label = all_labels[int(probs.argmax().item())]
    # Busca a qué categoría pertenece la etiqueta
    for cloth_type, labels in _LABELS.items():
        if best_label in labels:
            return cloth_type
    # Valor por defecto si no hay match (no debería ocurrir)
    return "upper"

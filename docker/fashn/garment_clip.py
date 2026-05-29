"""Zero-shot garment type classifier using CLIP (runs inside the GPU inference container)."""

from __future__ import annotations

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

_LABELS: dict[str, list[str]] = {
    "upper": ["shirt", "blouse", "top", "jacket", "sweater", "hoodie"],
    "lower": ["pants", "skirt", "shorts", "jeans", "trousers"],
    "overall": ["dress", "jumpsuit", "romper", "overalls"],
}

_clip_model = None
_clip_processor = None


def _heuristic_cloth_type(image: Image.Image) -> str:
    """Fallback when CLIP is unavailable: infer type from garment aspect ratio."""
    w, h = image.size
    ratio = h / max(w, 1)
    if ratio >= 1.25:
        return "overall"
    if ratio >= 0.95:
        return "upper"
    return "lower"


def _get_clip():
    global _clip_model, _clip_processor
    if _clip_model is None:
        from transformers import CLIPModel, CLIPProcessor

        # safetensors avoids torch.load CVE guard on torch<2.6 in the base image.
        _clip_model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32",
            use_safetensors=True,
        )
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _clip_model, _clip_processor


def _detect_via_clip(garment_bytes: bytes) -> str:
    import torch

    model, processor = _get_clip()

    image = Image.open(io.BytesIO(garment_bytes)).convert("RGB")
    all_labels = [label for labels in _LABELS.values() for label in labels]

    inputs = processor(
        text=all_labels, images=image, return_tensors="pt", padding=True
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)[0]

    best_label = all_labels[int(probs.argmax().item())]
    for cloth_type, labels in _LABELS.items():
        if best_label in labels:
            return cloth_type
    return "upper"


def detect_cloth_type(garment_bytes: bytes) -> str:
    """Return 'upper' | 'lower' | 'overall'."""
    try:
        return _detect_via_clip(garment_bytes)
    except Exception as exc:
        image = Image.open(io.BytesIO(garment_bytes)).convert("RGB")
        result = _heuristic_cloth_type(image)
        logger.warning("CLIP classify failed (%s); heuristic=%s", exc, result)
        return result

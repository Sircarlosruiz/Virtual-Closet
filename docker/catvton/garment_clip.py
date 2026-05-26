"""Zero-shot garment type classifier using CLIP (runs only in the GPU inference container)."""

from __future__ import annotations

import io

from PIL import Image

_LABELS: dict[str, list[str]] = {
    "upper": ["shirt", "blouse", "top", "jacket", "sweater", "hoodie"],
    "lower": ["pants", "skirt", "shorts", "jeans", "trousers"],
    "overall": ["dress", "jumpsuit", "romper", "overalls"],
}

_clip_model = None
_clip_processor = None


def _get_clip():
    global _clip_model, _clip_processor
    if _clip_model is None:
        from transformers import CLIPModel, CLIPProcessor

        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _clip_model, _clip_processor


def detect_cloth_type(garment_bytes: bytes) -> str:
    """Return 'upper' | 'lower' | 'overall' using CLIP zero-shot classification."""
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

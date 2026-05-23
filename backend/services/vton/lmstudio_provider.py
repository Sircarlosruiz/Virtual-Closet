import base64
import io
import json
import logging
import re

import httpx
from PIL import Image

from core.config import settings
from services.vton.base import VTONProvider

logger = logging.getLogger(__name__)

_DEFAULT_PLACEMENT = {"scale": 0.42, "y_anchor": 0.48, "x_anchor": 0.5}

_PLACEMENT_SYSTEM_PROMPT = (
    "Eres un asistente de virtual try-on. Analiza imágenes de prenda y modelo "
    "y responde únicamente con JSON válido para colocar la prenda sobre la persona."
)


class LMStudioProvider(VTONProvider):
    """Dev provider: LM Studio native REST API + local compositing."""

    def __init__(self) -> None:
        self._root_url = self._normalize_root_url(settings.LMSTUDIO_BASE_URL)
        self._model = settings.LMSTUDIO_MODEL.strip()
        self._api_key = settings.LMSTUDIO_API_KEY or "lm-studio"
        self._system_prompt = (
            settings.LMSTUDIO_SYSTEM_PROMPT.strip() or _PLACEMENT_SYSTEM_PROMPT
        )

    async def generate(
        self, garment: bytes, model: bytes, cloth_type: str = "upper"
    ) -> bytes:
        from services.vton.garment_compositor import composite_garment_on_model

        if settings.LMSTUDIO_USE_PLACEMENT:
            model_id = await self._resolve_model_id()
            placement = await self._request_placement(model_id, garment, model)
            return self._composite_legacy(garment, model, placement)
        return composite_garment_on_model(garment, model)

    @staticmethod
    def _normalize_root_url(url: str) -> str:
        root = url.rstrip("/")
        for suffix in ("/api/v1", "/v1"):
            if root.endswith(suffix):
                root = root[: -len(suffix)]
                break
        return root

    @property
    def _chat_url(self) -> str:
        return f"{self._root_url}/api/v1/chat"

    @property
    def _models_url(self) -> str:
        return f"{self._root_url}/api/v1/models"

    async def _resolve_model_id(self) -> str:
        if self._model:
            return self._model

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                self._models_url,
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            payload = resp.json()

        for entry in payload.get("models") or []:
            loaded = entry.get("loaded_instances") or []
            if loaded:
                return loaded[0]["id"]

        raise RuntimeError(
            "LM Studio no tiene modelos cargados. Carga google/gemma-4-31b (o el modelo "
            "configurado) y activa el servidor local en Developer → Start Server."
        )

    async def _request_placement(
        self, model_id: str, garment: bytes, model: bytes
    ) -> dict[str, float]:
        garment_b64 = base64.b64encode(garment).decode()
        model_b64 = base64.b64encode(model).decode()
        prompt = (
            "Imagen 1 = prenda. Imagen 2 = persona/modelo. "
            "Responde SOLO con JSON válido, sin markdown:\n"
            '{"scale": 0.42, "y_anchor": 0.48, "x_anchor": 0.5}\n'
            "scale = ancho de la prenda como fracción del ancho del modelo (0.2-0.65).\n"
            "y_anchor = centro vertical de la prenda (0.3-0.7, 0=arriba).\n"
            "x_anchor = centro horizontal (0.5 = centro)."
        )

        body = {
            "model": model_id,
            "system_prompt": self._system_prompt,
            "input": [
                {"type": "text", "content": prompt},
                {"type": "image", "data_url": f"data:image/jpeg;base64,{garment_b64}"},
                {"type": "image", "data_url": f"data:image/jpeg;base64,{model_b64}"},
            ],
            "temperature": 0.1,
            "context_length": 4096,
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    self._chat_url,
                    headers={**self._auth_headers(), "Content-Type": "application/json"},
                    json=body,
                )
                resp.raise_for_status()
                payload = resp.json()
            content = self._extract_message_content(payload)
            placement = self._parse_placement(content)
            logger.info("LM Studio placement (%s): %s", model_id, placement)
            return placement
        except Exception as exc:
            logger.warning(
                "LM Studio chat no disponible (%s); usando composición por defecto",
                exc,
            )
            return dict(_DEFAULT_PLACEMENT)

    @staticmethod
    def _extract_message_content(payload: dict) -> str:
        parts: list[str] = []
        for item in payload.get("output") or []:
            if item.get("type") == "message" and item.get("content"):
                parts.append(str(item["content"]))
        return "\n".join(parts)

    def _parse_placement(self, content: str) -> dict[str, float]:
        match = re.search(r"\{[^{}]+\}", content)
        if not match:
            return dict(_DEFAULT_PLACEMENT)

        data = json.loads(match.group())
        scale = float(data.get("scale", _DEFAULT_PLACEMENT["scale"]))
        y_anchor = float(data.get("y_anchor", _DEFAULT_PLACEMENT["y_anchor"]))
        x_anchor = float(data.get("x_anchor", _DEFAULT_PLACEMENT["x_anchor"]))
        return {
            "scale": min(max(scale, 0.2), 0.65),
            "y_anchor": min(max(y_anchor, 0.25), 0.75),
            "x_anchor": min(max(x_anchor, 0.2), 0.8),
        }

    def _composite_legacy(
        self, garment_bytes: bytes, model_bytes: bytes, placement: dict[str, float]
    ) -> bytes:
        model_img = Image.open(io.BytesIO(model_bytes)).convert("RGBA")
        garment_img = Image.open(io.BytesIO(garment_bytes)).convert("RGBA")

        target_w = max(1, int(model_img.width * placement["scale"]))
        ratio = target_w / garment_img.width
        target_h = max(1, int(garment_img.height * ratio))
        garment_resized = garment_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        center_x = int(model_img.width * placement["x_anchor"])
        center_y = int(model_img.height * placement["y_anchor"])
        left = center_x - target_w // 2
        top = center_y - target_h // 2

        canvas = model_img.copy()
        canvas.alpha_composite(garment_resized, (left, top))
        output = canvas.convert("RGB")
        buf = io.BytesIO()
        output.save(buf, format="JPEG", quality=92)
        return buf.getvalue()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

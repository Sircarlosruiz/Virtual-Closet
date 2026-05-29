import io
import httpx
from services.vton.base import VTONProvider
from core.config import settings


class FashnLocalProvider(VTONProvider):
    """Self-hosted FASHN VTON v1.5 provider (maskless try-on, ~8 GB VRAM).

    Expects a running inference server at FASHN_LOCAL_URL exposing:
      POST /classify — multipart: garment (image/jpeg) → {"cloth_type": "upper"|...}
      POST /predict  — multipart: garment (image/jpeg), model (image/jpeg)
                       form fields: cloth_type (upper|lower|overall),
                                    garment_photo_type (model|flat-lay)
      GET  /health   — returns {"status": "ok"}

    Start the server with:
      docker compose --profile gpu up fashn
    """

    def __init__(self) -> None:
        self._endpoint = settings.FASHN_LOCAL_URL.rstrip("/")

    async def generate(
        self, garment: bytes, model: bytes, cloth_type: str = "upper"
    ) -> bytes:
        files = {
            "garment": ("garment.jpg", io.BytesIO(garment), "image/jpeg"),
            "model": ("model.jpg", io.BytesIO(model), "image/jpeg"),
        }
        data = {
            "cloth_type": cloth_type,
            "garment_photo_type": settings.FASHN_GARMENT_PHOTO_TYPE,
        }
        # ~5 s on H100; allow generous headroom for fp32 on Turing GPUs.
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self._endpoint}/predict",
                files=files,
                data=data,
            )
            resp.raise_for_status()
            return resp.content

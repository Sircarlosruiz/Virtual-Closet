import io
import httpx
from services.vton.base import VTONProvider
from core.config import settings


class CatVTONLocalProvider(VTONProvider):
    """Self-hosted CatVTON-Flux provider.

    Expects a running inference server at CATVTON_LOCAL_URL exposing:
      POST /predict  — multipart: garment (image/jpeg), model (image/jpeg)
                       form field: cloth_type (upper|lower|overall)
      GET  /health   — returns {"status": "ok"}

    Start the server with:
      docker compose --profile gpu up catvton
    """

    def __init__(self) -> None:
        self._endpoint = settings.CATVTON_LOCAL_URL

    async def generate(self, garment: bytes, model: bytes) -> bytes:
        files = {
            "garment": ("garment.jpg", io.BytesIO(garment), "image/jpeg"),
            "model": ("model.jpg", io.BytesIO(model), "image/jpeg"),
        }
        data = {"cloth_type": settings.CATVTON_CLOTH_TYPE}
        # FLUX inpainting at 1024px takes 60-120 s on an RTX 4090
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self._endpoint}/predict",
                files=files,
                data=data,
            )
            resp.raise_for_status()
            return resp.content

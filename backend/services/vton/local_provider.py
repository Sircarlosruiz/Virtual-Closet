import io
import httpx
from services.vton.base import VTONProvider


class LocalProvider(VTONProvider):
    def __init__(self, endpoint: str | None = None) -> None:
        from core.config import settings

        self._endpoint = endpoint or settings.VTON_LOCAL_URL

    async def generate(self, garment: bytes, model: bytes) -> bytes:
        files = {
            "garment": ("garment.jpg", io.BytesIO(garment), "image/jpeg"),
            "model": ("model.jpg", io.BytesIO(model), "image/jpeg"),
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self._endpoint}/predict", files=files)
            resp.raise_for_status()
            return resp.content

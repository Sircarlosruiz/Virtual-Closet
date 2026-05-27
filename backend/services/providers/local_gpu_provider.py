import httpx

from core.config import settings
from services.providers.vton_provider import VTONProvider


class LocalGPUProvider(VTONProvider):
    """Development provider — calls local IDM-VTON service."""

    def __init__(self) -> None:
        self._base_url = settings.VTON_LOCAL_URL

    async def generate(
        self, garment_url: str, model_url: str, cloth_type: str
    ) -> bytes:
        """Download images from URLs and send to local VTON service."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Download garment and model images
            garment_resp = await client.get(garment_url)
            garment_resp.raise_for_status()
            model_resp = await client.get(model_url)
            model_resp.raise_for_status()

            # Send to local VTON service
            files = {
                "garment_image": ("garment.jpg", garment_resp.content, "image/jpeg"),
                "model_image": ("model.jpg", model_resp.content, "image/jpeg"),
            }
            data = {"cloth_type": cloth_type}

            resp = await client.post(
                f"{self._base_url}/generate",
                files=files,
                data=data,
            )
            resp.raise_for_status()
            return resp.content

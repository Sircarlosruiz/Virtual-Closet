from services.vton.base import VTONProvider
from services.vton.garment_compositor import composite_garment_on_model


class ComposeProvider(VTONProvider):
    """Dev provider: background removal + seamless blending (no LLM)."""

    async def generate(self, garment: bytes, model: bytes) -> bytes:
        return composite_garment_on_model(garment, model)

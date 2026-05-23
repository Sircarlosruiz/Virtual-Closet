import asyncio
import base64
import httpx
import replicate
from services.vton.base import VTONProvider
from core.config import settings


class CatVTONReplicateProvider(VTONProvider):
    """Replicate-hosted CatVTON-Flux provider.

    Model page: https://replicate.com — search for the model set in
    CATVTON_REPLICATE_MODEL and verify the exact input schema before use.
    Common schema: human_image, cloth_image, cloth_type.
    """

    def __init__(self) -> None:
        if not settings.REPLICATE_API_KEY.strip():
            raise ValueError(
                "REPLICATE_API_KEY no configurada. "
                "Obtenla en https://replicate.com/account/api-tokens"
            )
        self._client = replicate.Client(api_token=settings.REPLICATE_API_KEY)

    async def generate(self, garment: bytes, model: bytes) -> bytes:
        garment_uri = f"data:image/jpeg;base64,{base64.b64encode(garment).decode()}"
        model_uri = f"data:image/jpeg;base64,{base64.b64encode(model).decode()}"

        def _run() -> object:
            return self._client.run(
                settings.CATVTON_REPLICATE_MODEL,
                input={
                    "human_image": model_uri,
                    "cloth_image": garment_uri,
                    "cloth_type": settings.CATVTON_CLOTH_TYPE,
                    "num_inference_steps": 50,
                    "guidance_scale": 30.0,
                },
            )

        output = await asyncio.to_thread(_run)

        # Replicate SDK ≥0.20 returns FileOutput objects; str() gives the URL.
        if isinstance(output, list) and output:
            result_url = str(output[0])
        elif hasattr(output, "url"):
            result_url = output.url
        elif isinstance(output, str):
            result_url = output
        else:
            raise RuntimeError(f"Unexpected Replicate output: {type(output)}")

        async with httpx.AsyncClient(timeout=120.0) as http:
            resp = await http.get(result_url)
            resp.raise_for_status()
            return resp.content

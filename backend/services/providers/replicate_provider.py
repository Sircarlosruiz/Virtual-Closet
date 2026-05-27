import httpx

from core.config import settings
from services.providers.vton_provider import VTONProvider


class ReplicateProvider(VTONProvider):
    """Production provider — calls Replicate API for CatVTON inference."""

    def __init__(self) -> None:
        if not settings.REPLICATE_API_KEY.strip():
            raise ValueError(
                "REPLICATE_API_KEY not configured. Get a token at "
                "https://replicate.com/account/api-tokens and add it to backend/.env"
            )
        self._api_key = settings.REPLICATE_API_KEY
        self._model = settings.CATVTON_REPLICATE_MODEL

    async def generate(
        self, garment_url: str, model_url: str, cloth_type: str
    ) -> bytes:
        """Run CatVTON inference via Replicate API."""
        # Map cloth_type to Replicate's expected format
        cloth_map = {
            "upper_body": "upper",
            "lower_body": "lower",
            "dress": "overall",
        }
        replicate_cloth_type = cloth_map.get(cloth_type, "upper")

        async with httpx.AsyncClient(timeout=180.0) as client:
            # Start prediction
            resp = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "version": self._model,
                    "input": {
                        "human_image": model_url,
                        "cloth_image": garment_url,
                        "cloth_type": replicate_cloth_type,
                    },
                },
            )
            resp.raise_for_status()
            prediction = resp.json()

            # Poll for completion
            prediction_url = prediction["urls"]["get"]
            for _ in range(60):  # Max 5 minutes (60 * 5s)
                import asyncio

                await asyncio.sleep(5)
                status_resp = await client.get(
                    prediction_url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()

                if status_data["status"] == "succeeded":
                    result_url = status_data["output"]
                    # Download result image
                    if isinstance(result_url, list):
                        result_url = result_url[0]
                    img_resp = await client.get(result_url)
                    img_resp.raise_for_status()
                    return img_resp.content
                elif status_data["status"] == "failed":
                    raise RuntimeError(
                        f"Replicate inference failed: {status_data.get('error', 'Unknown error')}"
                    )

            raise TimeoutError("Replicate inference timed out after 5 minutes")

import asyncio
import base64

import httpx
import replicate
from services.vton.base import VTONProvider
from core.config import settings
from services.usage_accounting_service import usage_from_prediction


def model_from_prediction(prediction: object) -> str:
    model = getattr(prediction, "model", None)
    if isinstance(model, str) and model.strip():
        return model.strip()
    return settings.CATVTON_REPLICATE_MODEL


class CatVTONReplicateProvider(VTONProvider):
    """Replicate-hosted CatVTON-Flux provider.

    Model page: https://replicate.com — search for the model set in
    CATVTON_REPLICATE_MODEL and verify the exact input schema before use.
    Common schema: human_image, cloth_image, cloth_type.

    After `generate`, `last_usage` / `last_model` hold sanitized prediction
    telemetry for the image-generation adapter sidecar (ADR-073). VTON callers
    continue to receive only image bytes.
    """

    def __init__(self) -> None:
        if not settings.REPLICATE_API_KEY.strip():
            raise ValueError(
                "REPLICATE_API_KEY no configurada. "
                "Obtenla en https://replicate.com/account/api-tokens"
            )
        self._client = replicate.Client(api_token=settings.REPLICATE_API_KEY)
        self.last_usage: dict[str, object] | None = None
        self.last_model: str | None = None

    async def generate(
        self, garment: bytes, model: bytes, cloth_type: str = "upper"
    ) -> bytes:
        self.last_usage = None
        self.last_model = None
        garment_uri = f"data:image/jpeg;base64,{base64.b64encode(garment).decode()}"
        model_uri = f"data:image/jpeg;base64,{base64.b64encode(model).decode()}"
        payload = {
            "human_image": model_uri,
            "cloth_image": garment_uri,
            "cloth_type": cloth_type,
            "num_inference_steps": 50,
            "guidance_scale": 30.0,
        }

        def _run() -> object:
            predictions_api = getattr(self._client, "predictions", None)
            create = getattr(predictions_api, "create", None) if predictions_api else None
            if create is not None:
                prediction = create(
                    model=settings.CATVTON_REPLICATE_MODEL,
                    input=payload,
                )
                wait = getattr(prediction, "wait", None)
                if callable(wait):
                    wait()
                return prediction
            return self._client.run(settings.CATVTON_REPLICATE_MODEL, input=payload)

        output = await asyncio.to_thread(_run)
        if hasattr(output, "output") or hasattr(output, "metrics"):
            self.last_usage = usage_from_prediction(output)
            self.last_model = model_from_prediction(output)
            output = getattr(output, "output", output)

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

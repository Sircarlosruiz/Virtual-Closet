import io
import base64
import replicate
from services.vton.base import VTONProvider
from core.config import settings


class ReplicateProvider(VTONProvider):
    def __init__(self) -> None:
        self._client = replicate.Client(api_token=settings.REPLICATE_API_KEY)

    async def generate(self, garment: bytes, model: bytes) -> bytes:
        garment_b64 = base64.b64encode(garment).decode()
        model_b64 = base64.b64encode(model).decode()

        output = self._client.run(
            "cuuupid/idm-vton",
            input={
                "garm_img": f"data:image/jpeg;base64,{garment_b64}",
                "model_img": f"data:image/jpeg;base64,{model_b64}",
            },
        )

        if isinstance(output, list) and len(output) > 0:
            result_url = output[0]
        elif isinstance(output, str):
            result_url = output
        else:
            raise RuntimeError(f"Unexpected output from Replicate: {type(output)}")

        import httpx
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(result_url)
            resp.raise_for_status()
            return resp.content

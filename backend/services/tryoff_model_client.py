import httpx

from core.config import settings


class TryoffModelClientError(Exception):
    """Raised when the TryOff model service call fails."""


class TryoffModelClient:
    """HTTP client for the TryOff FLUX model service."""

    def __init__(self) -> None:
        self._base_url = settings.TRYOFF_MODEL_URL
        self._timeout = settings.TRYOFF_MODEL_TIMEOUT_SECONDS

    async def extract_garment(
        self,
        source_image_url: str,
        garment_type: str,
    ) -> bytes:
        """Call the FLUX model service to extract a garment from a source image.

        Args:
            source_image_url: Presigned URL to the source image in MinIO.
            garment_type: One of 'upper', 'lower', 'dress'.

        Returns:
            Raw PNG bytes of the extracted garment.

        Raises:
            TryoffModelClientError: If the model service returns an error.
        """
        try:
            download_timeout = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
            inference_timeout = httpx.Timeout(
                connect=30.0,
                read=float(self._timeout),
                write=120.0,
                pool=30.0,
            )

            async with httpx.AsyncClient(timeout=download_timeout) as client:
                image_response = await client.get(source_image_url)
                image_response.raise_for_status()
                image_bytes = image_response.content

            async with httpx.AsyncClient(timeout=inference_timeout) as client:
                response = await client.post(
                    f"{self._base_url}/tryoff",
                    files={"image": ("source.jpg", image_bytes, "image/jpeg")},
                    data={"garment_type": garment_type},
                )

                if response.status_code == 503:
                    raise TryoffModelClientError(
                        f"Model service unavailable: {response.text}"
                    )
                if response.status_code == 504:
                    raise TryoffModelClientError(
                        f"Model service timeout: {response.text}"
                    )
                if response.status_code != 200:
                    raise TryoffModelClientError(
                        f"Model service error {response.status_code}: {response.text}"
                    )

                return response.content

        except httpx.TimeoutException as exc:
            raise TryoffModelClientError(f"Request timeout: {exc}") from exc
        except httpx.ConnectError as exc:
            raise TryoffModelClientError(
                "TryOff model service is not reachable at "
                f"{self._base_url}. Start it with: "
                "docker compose --profile gpu up -d tryoff-model "
                "(or: make flux-restart)"
            ) from exc
        except httpx.HTTPError as exc:
            raise TryoffModelClientError(f"HTTP error: {exc}") from exc

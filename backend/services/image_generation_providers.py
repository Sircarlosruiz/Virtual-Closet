from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import httpx

from core.config import settings

_OPENAI_BASE_URL = "https://api.openai.com/v1"
_OPENAI_IMAGE_MODEL = "gpt-image-1"
_REQUEST_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class ProviderInvocationResult:
    image_bytes: bytes
    provider_model: str
    usage: Mapping[str, object] | None


class ProviderRateLimitedError(Exception):
    """Provider returned 429; retry_after_seconds may be present."""

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        super().__init__("Provider rate limited the request")
        self.retry_after_seconds = retry_after_seconds


class ProviderTimeoutError(Exception):
    """Provider did not respond before the configured timeout — unknown outcome."""


class ProviderNoResultError(Exception):
    """Provider responded without a usable image."""


class ProviderRequestError(Exception):
    """Non-retryable provider or application error (bad request, unsupported mode)."""


class ImageGenerationProvider(Protocol):
    async def generate(self, inputs: Mapping[str, object]) -> ProviderInvocationResult:
        """Generate an image from sanitized, application-owned inputs."""


def _extract_retry_after(response: httpx.Response) -> int | None:
    header = response.headers.get("retry-after")
    if header is None:
        return None
    try:
        return int(header)
    except ValueError:
        return None


class OpenAIImageProvider:
    """Server-side boundary for OpenAI image generation.

    Credentials are resolved only here, inside worker context (ADR-047).
    `text` mode calls the generations endpoint directly. Modes that require
    composing reference images (`edit`, `extraction`, `try_on` with the
    `openai` provider) are not yet wired to image resolution — that spans
    the media library owned by other units — and raise a clearly classified
    `ProviderRequestError` rather than guessing at a contract.
    """

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY.strip():
            raise ValueError("OPENAI_API_KEY is not configured")
        self._api_key = settings.OPENAI_API_KEY

    async def generate(self, inputs: Mapping[str, object]) -> ProviderInvocationResult:
        mode = inputs.get("mode")
        if mode == "text":
            return await self._generate_from_text(str(inputs.get("prompt", "")))
        raise ProviderRequestError(f"OpenAI mode '{mode}' is not yet supported by this adapter")

    async def _generate_from_text(self, prompt: str) -> ProviderInvocationResult:
        if not prompt.strip():
            raise ProviderRequestError("A non-empty prompt is required for text generation")

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{_OPENAI_BASE_URL}/images/generations",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": _OPENAI_IMAGE_MODEL, "prompt": prompt, "n": 1},
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError() from exc
        except httpx.ConnectError as exc:
            raise ProviderTimeoutError() from exc

        if response.status_code == 429:
            raise ProviderRateLimitedError(_extract_retry_after(response))
        if response.status_code >= 400:
            raise ProviderRequestError(
                f"OpenAI image generation failed with status {response.status_code}"
            )

        payload = response.json()
        data = payload.get("data") or []
        if not data or not data[0].get("b64_json"):
            raise ProviderNoResultError()

        import base64

        image_bytes = base64.b64decode(data[0]["b64_json"])
        return ProviderInvocationResult(
            image_bytes=image_bytes,
            provider_model=_OPENAI_IMAGE_MODEL,
            usage=payload.get("usage"),
        )

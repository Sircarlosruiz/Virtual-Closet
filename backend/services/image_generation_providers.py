from collections.abc import Mapping
from typing import Protocol

from core.config import settings


class ImageGenerationProvider(Protocol):
    async def generate(self, inputs: Mapping[str, object]) -> bytes:
        """Generate an image from sanitized, application-owned inputs."""


class OpenAIImageProvider:
    """Server-side boundary for OpenAI image generation.

    The API client is intentionally added by the reliability/integration bolt;
    this boundary ensures credentials are resolved only in worker context.
    """

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY.strip():
            raise ValueError("OPENAI_API_KEY is not configured")
        self._api_key = settings.OPENAI_API_KEY

    async def generate(self, inputs: Mapping[str, object]) -> bytes:
        del inputs
        raise NotImplementedError("OpenAI execution is implemented by the reliability bolt")

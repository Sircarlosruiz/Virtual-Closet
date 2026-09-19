"""Per-provider call timeouts for image generation (NFR-3)."""

from dataclasses import dataclass

from core.config import settings
from services.image_generation_providers import ProviderRequestError


@dataclass(frozen=True)
class ProviderTimeout:
    provider: str
    seconds: int


class ProviderTimeoutPolicy:
    def timeout_for(self, provider: str) -> ProviderTimeout:
        if provider == "openai":
            return ProviderTimeout(
                provider=provider,
                seconds=int(settings.IMAGE_GENERATION_OPENAI_TIMEOUT_SECONDS),
            )
        if provider == "replicate":
            return ProviderTimeout(
                provider=provider,
                seconds=int(settings.IMAGE_GENERATION_REPLICATE_TIMEOUT_SECONDS),
            )
        raise ProviderRequestError(
            f"Provider '{provider}' execution is not yet wired to this worker"
        )

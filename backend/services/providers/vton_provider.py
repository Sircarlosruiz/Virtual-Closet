from abc import ABC, abstractmethod

from core.config import settings


class VTONProvider(ABC):
    """Abstract interface for VTON AI inference providers."""

    @abstractmethod
    async def generate(
        self, garment_url: str, model_url: str, cloth_type: str
    ) -> bytes:
        """Run VTON inference and return generated image bytes.

        Args:
            garment_url: Pre-signed URL for the garment image.
            model_url: Pre-signed URL for the model image.
            cloth_type: One of 'upper_body', 'lower_body', 'dress'.

        Returns:
            Generated try-on image as JPEG bytes.
        """
        ...


def get_vton_provider() -> VTONProvider:
    """Factory function that returns the configured VTON provider."""
    provider_type = settings.VTON_PROVIDER.lower()

    if provider_type == "local":
        from services.providers.local_gpu_provider import LocalGPUProvider

        return LocalGPUProvider()
    elif provider_type == "replicate":
        from services.providers.replicate_provider import ReplicateProvider

        return ReplicateProvider()
    else:
        raise ValueError(
            f"Unknown VTON_PROVIDER: '{provider_type}'. "
            "Must be 'local' or 'replicate'."
        )

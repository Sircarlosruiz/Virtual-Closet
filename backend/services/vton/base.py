from abc import ABC, abstractmethod


class VTONProvider(ABC):
    @abstractmethod
    async def generate(
        self, garment: bytes, model: bytes, cloth_type: str = "upper"
    ) -> bytes:
        """Generate virtual try-on image.

        Args:
            garment: Garment image bytes (JPEG)
            model: Model/person image bytes (JPEG)
            cloth_type: Type of garment — upper | lower | overall

        Returns:
            Generated try-on image bytes (JPEG)
        """
        ...

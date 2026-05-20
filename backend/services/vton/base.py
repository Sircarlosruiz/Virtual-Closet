from abc import ABC, abstractmethod


class VTONProvider(ABC):
    @abstractmethod
    async def generate(self, garment: bytes, model: bytes) -> bytes:
        """Generate virtual try-on image.

        Args:
            garment: Garment image bytes (JPEG)
            model: Model/person image bytes (JPEG)

        Returns:
            Generated try-on image bytes (JPEG)
        """
        ...

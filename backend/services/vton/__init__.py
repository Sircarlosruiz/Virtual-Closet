from services.vton.base import VTONProvider
from services.vton.replicate_provider import ReplicateProvider
from services.vton.local_provider import LocalProvider
from core.config import settings


def get_provider() -> VTONProvider:
    provider_type = settings.VTON_PROVIDER
    if provider_type == "local":
        return LocalProvider()
    return ReplicateProvider()

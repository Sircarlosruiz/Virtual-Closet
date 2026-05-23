from services.vton.base import VTONProvider
from services.vton.replicate_provider import ReplicateProvider
from services.vton.local_provider import LocalProvider
from services.vton.lmstudio_provider import LMStudioProvider
from services.vton.compose_provider import ComposeProvider
from core.config import settings


def get_provider() -> VTONProvider:
    provider_type = settings.VTON_PROVIDER
    if provider_type == "local":
        return LocalProvider()
    if provider_type == "compose":
        return ComposeProvider()
    if provider_type == "lmstudio":
        return LMStudioProvider()
    return ReplicateProvider()

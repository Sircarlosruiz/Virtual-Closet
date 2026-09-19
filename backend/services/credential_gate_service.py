"""Per-provider credential gate for image-generation workers (FR-10)."""

from dataclasses import dataclass

from core.config import settings
from services.image_generation_providers import ProviderRequestError

PROVIDER_CREDENTIAL_MISSING = "PROVIDER_CREDENTIAL_MISSING"

_PROVIDER_SETTINGS = {
    "openai": "OPENAI_API_KEY",
    "replicate": "REPLICATE_API_KEY",
}


class CredentialMissingError(Exception):
    """The job's provider is missing its server-side credential."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        self.error_code = PROVIDER_CREDENTIAL_MISSING
        super().__init__(f"Image generation is unavailable: {provider} is not configured")


@dataclass(frozen=True)
class CredentialRequirement:
    provider: str
    setting_name: str


class CredentialGateService:
    """Checks only the credential required by `job.provider` (ADR-047)."""

    def require(self, provider: str) -> CredentialRequirement:
        setting_name = _PROVIDER_SETTINGS.get(provider)
        if setting_name is None:
            raise ProviderRequestError(
                f"Provider '{provider}' execution is not yet wired to this worker"
            )
        value = getattr(settings, setting_name, "") or ""
        if not str(value).strip():
            raise CredentialMissingError(provider)
        return CredentialRequirement(provider=provider, setting_name=setting_name)

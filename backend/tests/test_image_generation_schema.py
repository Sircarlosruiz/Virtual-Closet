from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.schemas.image_generation import (
    GenerationMode,
    GenerationProvider,
    ImageGenerationRequest,
)


def test_accepts_try_on_for_replicate() -> None:
    request = ImageGenerationRequest(
        mode=GenerationMode.try_on,
        provider=GenerationProvider.replicate,
        garment_id=uuid4(),
        model_id=uuid4(),
        cloth_type="upper_body",
    )

    assert request.provider == GenerationProvider.replicate


def test_accepts_try_on_for_vton() -> None:
    request = ImageGenerationRequest(
        mode=GenerationMode.try_on,
        provider=GenerationProvider.vton,
        garment_id=uuid4(),
        model_id=uuid4(),
        cloth_type="upper_body",
    )

    assert request.provider == GenerationProvider.vton


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "text"},
        {"mode": "edit", "prompt": "replace background"},
        {"mode": "extraction"},
        {
            "mode": "try_on",
            "provider": "vton",
            "garment_id": uuid4(),
            "model_id": uuid4(),
        },
    ],
)
def test_rejects_missing_mode_inputs(payload: dict) -> None:
    with pytest.raises(ValidationError):
        ImageGenerationRequest.model_validate(payload)


def test_rejects_vton_for_text() -> None:
    with pytest.raises(ValidationError):
        ImageGenerationRequest(mode="text", provider="vton", prompt="a jacket")


def test_defaults_non_try_on_provider_to_openai() -> None:
    request = ImageGenerationRequest(mode="text", prompt="a jacket")

    assert request.provider is None


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "text", "prompt": "a jacket"},
        {
            "mode": "edit",
            "prompt": "replace background",
            "reference_image_ids": [uuid4()],
        },
        {"mode": "extraction", "reference_image_ids": [uuid4()]},
        {
            "mode": "try_on",
            "provider": "openai",
            "garment_id": uuid4(),
            "model_id": uuid4(),
            "cloth_type": "upper_body",
        },
    ],
)
def test_accepts_valid_mode_contracts(payload: dict) -> None:
    request = ImageGenerationRequest.model_validate(payload)

    assert request.mode.value == payload["mode"]

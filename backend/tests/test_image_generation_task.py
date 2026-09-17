from uuid import uuid4

import pytest

from tasks import image_generation as image_generation_task


def test_generate_image_task_is_registered_with_job_id_only_contract() -> None:
    task = image_generation_task.generate_image_task
    assert task.name == "tasks.generate_image"
    assert task.queue == "image.generation.normal"
    assert task.acks_late is True


def test_generate_image_task_rejects_invalid_job_id() -> None:
    with pytest.raises(ValueError):
        image_generation_task.generate_image_task.run("not-a-uuid")


def test_generate_image_task_requires_provider_configuration(monkeypatch) -> None:
    monkeypatch.setattr(image_generation_task.settings, "OPENAI_API_KEY", "   ")
    with pytest.raises(ValueError, match="provider is not configured"):
        image_generation_task.generate_image_task.run(str(uuid4()))

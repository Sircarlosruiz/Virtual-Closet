from unittest.mock import AsyncMock
from uuid import uuid4

from tasks import image_generation as image_generation_task
from tasks.image_generation import JobProcessResult


def test_generate_image_task_is_registered_with_job_id_only_contract() -> None:
    task = image_generation_task.generate_image_task
    assert task.name == "tasks.generate_image"
    assert task.queue == "image.generation.normal"
    assert task.acks_late is True


def test_generate_image_task_rejects_invalid_job_id() -> None:
    import pytest

    with pytest.raises(ValueError):
        image_generation_task.generate_image_task.run("not-a-uuid")


def test_generate_image_task_does_not_require_openai_key_at_entry(monkeypatch) -> None:
    monkeypatch.setattr(image_generation_task.settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(
        image_generation_task,
        "_process_job",
        AsyncMock(return_value=JobProcessResult()),
    )
    image_generation_task.generate_image_task.run(str(uuid4()))

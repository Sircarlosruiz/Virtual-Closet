from uuid import UUID

from core.celery_app import app
from core.config import settings


@app.task(
    bind=True,
    name="tasks.generate_image",
    acks_late=True,
    queue="image.generation.normal",
)
def generate_image_task(self, job_id: str) -> None:
    """Worker entry point; only a job ID crosses the broker boundary."""
    del self
    UUID(job_id)
    if not settings.OPENAI_API_KEY.strip():
        raise ValueError("Image generation is unavailable: provider is not configured")
    raise NotImplementedError("Image provider execution is implemented by the reliability bolt")

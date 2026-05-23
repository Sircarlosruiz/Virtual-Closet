from celery import Celery
from celery.signals import worker_ready
from core.config import settings

app = Celery(
    "vton",
    broker=settings.RABBITMQ_URL,
    backend="rpc://",
    include=["tasks.generate_vton"],
)

app.conf.task_routes = {
    "tasks.generate_vton": {"queue": "vton.generation.normal"},
}
app.conf.task_acks_late = True
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"
app.conf.task_default_queue = "vton.generation.normal"
app.conf.task_queues = {
    "vton.generation.normal": {},
    "vton.generation.priority": {},
    "vton.generation.dead": {},
}


@worker_ready.connect
def ensure_buckets_on_worker_start(**_kwargs) -> None:
    try:
        from core.minio_buckets import ensure_minio_buckets_sync

        ensure_minio_buckets_sync()
    except Exception:
        pass

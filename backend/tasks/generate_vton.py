import io
import json
from uuid import UUID

from core.celery_app import app
from core.config import settings
from core.minio_buckets import ensure_minio_buckets_sync
from services.storage_service import StorageService
from PIL import Image


def _get_storage() -> StorageService:
    return StorageService()


def _sync_send_ws(mayorista_id: UUID, message: dict) -> None:
    """Send WebSocket message synchronously using sync wrapper."""
    import asyncio
    from services.connection_manager import manager
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            manager.send(mayorista_id, json.dumps(message))
        )
        loop.close()
    except Exception:
        pass


def _run_vton_provider(
    garment_bytes: bytes, model_bytes: bytes, cloth_type: str = "upper"
) -> bytes:
    """Run async VTON provider synchronously."""
    if settings.VTON_PROVIDER == "replicate" and not settings.REPLICATE_API_KEY.strip():
        raise ValueError(
            "REPLICATE_API_KEY no configurada. Obtén un token en "
            "https://replicate.com/account/api-tokens y añádelo en backend/.env, "
            "luego reinicia el worker: docker compose up -d celery_worker"
        )

    import asyncio
    from services.vton import get_provider

    provider = get_provider()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            provider.generate(garment_bytes, model_bytes, cloth_type)
        )
        return result
    finally:
        loop.close()


@app.task(
    bind=True,
    name="tasks.generate_vton",
    max_retries=3,
    acks_late=True,
    queue="vton.generation.normal",
)
def generate_vton_task(self, generacion_id: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.generacion import Generacion
    from models.prenda import Prenda
    from models.modelo_ia import ModeloIA

    ensure_minio_buckets_sync()
    storage = _get_storage()

    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(sync_url)
    Session = sessionmaker(engine)
    session = Session()

    try:
        generacion = session.query(Generacion).filter(Generacion.id == UUID(generacion_id)).first()
        if not generacion:
            raise ValueError(f"Generacion {generacion_id} not found")

        prenda = session.query(Prenda).filter(Prenda.id == generacion.prenda_id).first()
        if not prenda:
            raise ValueError(f"Prenda {generacion.prenda_id} not found")

        modelo = session.query(ModeloIA).filter(ModeloIA.id == generacion.modelo_ia_id).first()
        if not modelo:
            raise ValueError(f"ModeloIA {generacion.modelo_ia_id} not found")

        garment_key = prenda.imagen_original_key or StorageService.key_from_originals_url(
            prenda.imagen_original_url
        )
        model_key = modelo.thumbnail_key

        if not storage.object_exists_sync(garment_key, bucket_override="originals"):
            raise ValueError(
                f"Imagen de prenda no encontrada en MinIO (key={garment_key}). "
                "Vuelve a subir la prenda."
            )
        if not storage.object_exists_sync(model_key, bucket_override="model-thumbnails"):
            raise ValueError(
                f"Imagen de modelo no encontrada en MinIO (key={model_key}). "
                "Vuelve a crear o seleccionar el modelo."
            )

        garment_bytes = storage.get_object_bytes_sync(garment_key, bucket_override="originals")
        model_bytes = storage.get_object_bytes_sync(model_key, bucket_override="model-thumbnails")

        from services.vton.cloth_type_resolver import resolve_cloth_type

        cloth_type = resolve_cloth_type(garment_bytes)

        result_bytes = _run_vton_provider(garment_bytes, model_bytes, cloth_type)

        generated_key = f"{generacion.mayorista_id}/{generacion.id}.jpg"
        thumbnail_key = f"{generacion.mayorista_id}/{generacion.id}.jpg"

        storage.upload_bytes_sync(generated_key, result_bytes, bucket_override="generated")

        img = Image.open(io.BytesIO(result_bytes))
        img.thumbnail((400, 400))
        thumb_buf = io.BytesIO()
        img.save(thumb_buf, format="JPEG")
        storage.upload_bytes_sync(thumbnail_key, thumb_buf.getvalue(), bucket_override="thumbnails")

        generacion.estado = "lista"
        generacion.imagen_generada_key = generated_key
        generacion.thumbnail_key = thumbnail_key
        session.commit()

        _sync_send_ws(generacion.mayorista_id, {
            "type": "generacion_completada",
            "generacion_id": generacion_id,
        })

    except Exception as exc:
        from replicate.exceptions import ReplicateError

        auth_failure = (
            isinstance(exc, ReplicateError) and getattr(exc, "status", None) == 401
        ) or (
            isinstance(exc, ValueError) and "REPLICATE_API_KEY" in str(exc)
        )
        will_retry = self.request.retries < self.max_retries and not auth_failure
        try:
            session.rollback()
            generacion = session.query(Generacion).filter(Generacion.id == UUID(generacion_id)).first()
            if generacion and not will_retry:
                generacion.estado = "error"
                generacion.error_message = str(exc)
                session.commit()

                _sync_send_ws(generacion.mayorista_id, {
                    "type": "generacion_error",
                    "generacion_id": generacion_id,
                    "error": str(exc),
                })
        except Exception:
            pass

        if will_retry:
            raise self.retry(exc=exc)
        raise

    finally:
        session.close()
